"""
One-time cleanup script for QA test accounts and their data.

Matches:
- Users with emails matching ``qa_%@example.com`` (case-sensitive prefix ``qa_``)
  or belonging to a matched QA tenant
- Tenants with names matching ``QA_%`` (case-sensitive prefix ``QA_``)
- All associated collections, documents, chunks, ingestion jobs, query logs,
  query citations, and query feedback.

Defaults to dry-run (read-only preview with rollback). Pass --execute to commit deletions.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import ColumnElement, delete, func, or_, select
from sqlalchemy.engine.url import make_url
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import Mapped

# Ensure repository root is importable when invoked as `python scripts/cleanup_qa_accounts.py`
REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.core.config import Settings, settings  # noqa: E402
from app.db.session import create_app_engine  # noqa: E402
from app.models.chunk import Chunk  # noqa: E402
from app.models.collection import Collection  # noqa: E402
from app.models.document import Document  # noqa: E402
from app.models.feedback import QueryFeedback  # noqa: E402
from app.models.job import IngestionJob  # noqa: E402
from app.models.query_log import QueryCitation, QueryLog  # noqa: E402
from app.models.tenant import Tenant  # noqa: E402
from app.models.user import User  # noqa: E402


@dataclass
class CleanupPlan:
    tenants: list[Tenant]
    users: list[User]
    collections: list[Collection]
    documents: list[Document]
    query_log_samples: list[QueryLog]
    tenant_ids: list[uuid.UUID]
    user_ids: list[uuid.UUID]
    collection_ids: list[uuid.UUID]
    document_ids: list[uuid.UUID]
    chunk_ids: list[uuid.UUID]
    job_ids: list[uuid.UUID]
    query_log_ids: list[uuid.UUID]
    citation_count: int
    feedback_ids: list[uuid.UUID]
    non_qa_tenants_for_qa_users: list[tuple[str, str]]
    near_miss_users: list[str]
    near_miss_tenants: list[str]

    @property
    def total_rows(self) -> int:
        return (
            len(self.tenant_ids)
            + len(self.user_ids)
            + len(self.collection_ids)
            + len(self.document_ids)
            + len(self.query_log_ids)
            + len(self.chunk_ids)
            + len(self.job_ids)
            + self.citation_count
            + len(self.feedback_ids)
        )


def _redact_db_url(raw_url: str) -> str:
    try:
        return make_url(raw_url).render_as_string(hide_password=True)
    except Exception:
        return "<unparseable DATABASE_URL>"


async def _fetch_ids(
    session: AsyncSession,
    model_col: Mapped[uuid.UUID],
    filters: list[ColumnElement[bool]],
) -> list[uuid.UUID]:
    if not filters:
        return []
    result = await session.execute(select(model_col).where(or_(*filters)))
    return list(result.scalars().all())


async def build_cleanup_plan(session: AsyncSession) -> CleanupPlan:
    qa_tenant_cond = Tenant.name.like("QA\\_%", escape="\\")
    qa_user_email_cond = User.email.like("qa\\_%@example.com", escape="\\")

    tenants = list(
        (await session.execute(select(Tenant).where(qa_tenant_cond).order_by(Tenant.created_at))).scalars().all()
    )
    tenant_ids = [t.id for t in tenants]

    direct_email_users = list(
        (await session.execute(select(User).where(qa_user_email_cond).order_by(User.created_at))).scalars().all()
    )
    tenant_member_users = (
        list(
            (await session.execute(select(User).where(User.tenant_id.in_(tenant_ids)).order_by(User.created_at)))
            .scalars()
            .all()
        )
        if tenant_ids
        else []
    )

    users_by_id: dict[uuid.UUID, User] = {u.id: u for u in direct_email_users}
    for u in tenant_member_users:
        users_by_id.setdefault(u.id, u)
    users = sorted(users_by_id.values(), key=lambda u: u.created_at)
    user_ids = [u.id for u in users]

    tenant_id_set = set(tenant_ids)
    orphan_user_tenant_ids = list({u.tenant_id for u in direct_email_users if u.tenant_id not in tenant_id_set})
    non_qa_tenants_for_qa_users: list[tuple[str, str]] = []
    if orphan_user_tenant_ids:
        other_tenants = (
            await session.execute(select(Tenant).where(Tenant.id.in_(orphan_user_tenant_ids)))
        ).scalars().all()
        other_map = {t.id: t.name for t in other_tenants}
        for u in direct_email_users:
            if u.tenant_id in other_map:
                non_qa_tenants_for_qa_users.append((u.email, other_map[u.tenant_id]))

    collections = (
        list(
            (
                await session.execute(
                    select(Collection).where(Collection.tenant_id.in_(tenant_ids)).order_by(Collection.created_at)
                )
            )
            .scalars()
            .all()
        )
        if tenant_ids
        else []
    )
    collection_ids = [c.id for c in collections]

    doc_filters: list[ColumnElement[bool]] = []
    if tenant_ids:
        doc_filters.append(Document.tenant_id.in_(tenant_ids))
    if collection_ids:
        doc_filters.append(Document.collection_id.in_(collection_ids))
    documents = (
        list(
            (await session.execute(select(Document).where(or_(*doc_filters)).order_by(Document.created_at)))
            .scalars()
            .all()
        )
        if doc_filters
        else []
    )
    document_ids = [d.id for d in documents]

    chunk_filters: list[ColumnElement[bool]] = []
    if document_ids:
        chunk_filters.append(Chunk.document_id.in_(document_ids))
    if tenant_ids:
        chunk_filters.append(Chunk.tenant_id.in_(tenant_ids))
    if collection_ids:
        chunk_filters.append(Chunk.collection_id.in_(collection_ids))
    chunk_ids = await _fetch_ids(session, Chunk.id, chunk_filters)

    job_filters: list[ColumnElement[bool]] = []
    if tenant_ids:
        job_filters.append(IngestionJob.tenant_id.in_(tenant_ids))
    if document_ids:
        job_filters.append(IngestionJob.document_id.in_(document_ids))
    job_ids = await _fetch_ids(session, IngestionJob.id, job_filters)

    qlog_filters: list[ColumnElement[bool]] = []
    if tenant_ids:
        qlog_filters.append(QueryLog.tenant_id.in_(tenant_ids))
    if user_ids:
        qlog_filters.append(QueryLog.user_id.in_(user_ids))
    query_log_ids = await _fetch_ids(session, QueryLog.id, qlog_filters)
    query_log_samples = (
        list(
            (
                await session.execute(
                    select(QueryLog).where(QueryLog.id.in_(query_log_ids)).order_by(QueryLog.created_at.desc()).limit(10)
                )
            )
            .scalars()
            .all()
        )
        if query_log_ids
        else []
    )

    cit_filters: list[ColumnElement[bool]] = []
    if query_log_ids:
        cit_filters.append(QueryCitation.query_id.in_(query_log_ids))
    if chunk_ids:
        cit_filters.append(QueryCitation.chunk_id.in_(chunk_ids))
    citation_count = (
        int(
            (
                await session.execute(
                    select(func.count()).select_from(QueryCitation).where(or_(*cit_filters))
                )
            ).scalar_one()
        )
        if cit_filters
        else 0
    )

    fb_filters: list[ColumnElement[bool]] = []
    if tenant_ids:
        fb_filters.append(QueryFeedback.tenant_id.in_(tenant_ids))
    if user_ids:
        fb_filters.append(QueryFeedback.user_id.in_(user_ids))
    if query_log_ids:
        fb_filters.append(QueryFeedback.query_id.in_(query_log_ids))
    feedback_ids = await _fetch_ids(session, QueryFeedback.id, fb_filters)

    near_miss_users = list(
        (
            await session.execute(
                select(User.email)
                .where(User.email.ilike("%qa%"), ~qa_user_email_cond)
                .order_by(User.created_at)
                .limit(20)
            )
        )
        .scalars()
        .all()
    )
    near_miss_tenants = list(
        (
            await session.execute(
                select(Tenant.name)
                .where(Tenant.name.ilike("%qa%"), ~qa_tenant_cond)
                .order_by(Tenant.created_at)
                .limit(20)
            )
        )
        .scalars()
        .all()
    )

    return CleanupPlan(
        tenants=tenants,
        users=users,
        collections=collections,
        documents=documents,
        query_log_samples=query_log_samples,
        tenant_ids=tenant_ids,
        user_ids=user_ids,
        collection_ids=collection_ids,
        document_ids=document_ids,
        chunk_ids=chunk_ids,
        job_ids=job_ids,
        query_log_ids=query_log_ids,
        citation_count=citation_count,
        feedback_ids=feedback_ids,
        non_qa_tenants_for_qa_users=non_qa_tenants_for_qa_users,
        near_miss_users=near_miss_users,
        near_miss_tenants=near_miss_tenants,
    )


def print_plan(plan: CleanupPlan, db_display: str) -> None:
    print(f"Target database: {db_display}")
    print("\n=== QA CLEANUP PREVIEW ===")
    print(f"Tenants to delete     : {len(plan.tenant_ids)}")
    print(f"Users to delete       : {len(plan.user_ids)}")
    print(f"Collections to delete : {len(plan.collection_ids)}")
    print(f"Documents to delete   : {len(plan.document_ids)}")
    print(f"Query logs to delete  : {len(plan.query_log_ids)}")
    print(
        f"Dependent rows        : chunks={len(plan.chunk_ids)}, "
        f"ingestion_jobs={len(plan.job_ids)}, "
        f"query_citations={plan.citation_count}, "
        f"query_feedback={len(plan.feedback_ids)}"
    )

    if plan.tenants:
        print("\nMatched Tenants (name LIKE 'QA\\_%'):")
        for t in plan.tenants:
            print(f"  - {t.name} (id={t.id}, created_at={t.created_at.isoformat()})")

    if plan.users:
        print("\nMatched Users (email LIKE 'qa\\_%@example.com' OR member of matched QA tenant):")
        for u in plan.users:
            print(f"  - {u.email} [role={u.role}] (id={u.id}, tenant_id={u.tenant_id})")

    if plan.collections:
        print("\nMatched Collections:")
        for c in plan.collections:
            print(f"  - {c.name} (id={c.id}, tenant_id={c.tenant_id})")

    if plan.documents:
        print("\nMatched Documents:")
        for d in plan.documents:
            print(f"  - {d.title} [status={d.status}] (id={d.id}, collection_id={d.collection_id})")

    if plan.query_log_samples:
        print(f"\nSample Query Logs (showing up to 10 of {len(plan.query_log_ids)}):")
        for q in plan.query_log_samples:
            snippet = q.question.replace("\n", " ")[:70]
            print(f"  - [{q.created_at.isoformat()}] {q.id}: {snippet!r}")

    if plan.non_qa_tenants_for_qa_users:
        print("\n[WARNING] QA-email users belonging to non-QA_* tenants (those tenants will NOT be deleted):")
        for email, tenant_name in plan.non_qa_tenants_for_qa_users:
            print(f"  - user={email} -> tenant={tenant_name}")

    if plan.near_miss_users or plan.near_miss_tenants:
        print("\n[INFO] Non-matching records containing 'qa' (NOT selected for deletion):")
        for email in plan.near_miss_users:
            print(f"  - user: {email}")
        for name in plan.near_miss_tenants:
            print(f"  - tenant: {name}")


async def execute_cleanup(session: AsyncSession, plan: CleanupPlan) -> dict[str, int]:
    deleted: dict[str, int] = {}

    if plan.feedback_ids:
        res = await session.execute(delete(QueryFeedback).where(QueryFeedback.id.in_(plan.feedback_ids)))
        deleted["query_feedback"] = int(res.rowcount or 0)  # type: ignore[attr-defined]

    cit_filters: list[ColumnElement[bool]] = []
    if plan.query_log_ids:
        cit_filters.append(QueryCitation.query_id.in_(plan.query_log_ids))
    if plan.chunk_ids:
        cit_filters.append(QueryCitation.chunk_id.in_(plan.chunk_ids))
    if cit_filters:
        res = await session.execute(delete(QueryCitation).where(or_(*cit_filters)))
        deleted["query_citations"] = int(res.rowcount or 0)  # type: ignore[attr-defined]

    for label, model, ids in (
        ("query_logs", QueryLog, plan.query_log_ids),
        ("ingestion_jobs", IngestionJob, plan.job_ids),
        ("chunks", Chunk, plan.chunk_ids),
        ("documents", Document, plan.document_ids),
        ("collections", Collection, plan.collection_ids),
        ("users", User, plan.user_ids),
        ("tenants", Tenant, plan.tenant_ids),
    ):
        if ids:
            res = await session.execute(delete(model).where(model.id.in_(ids)))
            deleted[label] = int(res.rowcount or 0)  # type: ignore[attr-defined]

    return deleted


async def run(database_url: str, execute: bool) -> None:
    normalized_url = Settings.assemble_db_url(database_url)
    engine = create_app_engine(normalized_url)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    try:
        async with session_factory() as session:
            plan = await build_cleanup_plan(session)
            print_plan(plan, _redact_db_url(normalized_url))

            if plan.total_rows == 0:
                print("\nNothing to delete.")
                await session.rollback()
                return

            if not execute:
                await session.rollback()
                print("\nDRY RUN ONLY: no changes were committed. Re-run with --execute to delete these records.")
                return

            deleted = await execute_cleanup(session, plan)
            await session.commit()
            print("\nEXECUTED DELETION:")
            for table_name, count in deleted.items():
                print(f"  - {table_name}: {count}")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Preview and delete QA test accounts (qa_%@example.com, QA_* tenants) and their records."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL") or settings.DATABASE_URL,
        help="PostgreSQL connection URL (defaults to DATABASE_URL env var or app .env setting).",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually commit deletions. Without this flag, runs in dry-run preview mode.",
    )
    args = parser.parse_args()
    asyncio.run(run(args.database_url, execute=args.execute))


if __name__ == "__main__":
    main()
