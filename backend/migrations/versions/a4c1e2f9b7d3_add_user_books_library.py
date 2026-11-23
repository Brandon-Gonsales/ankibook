"""add user_books library for public books

Revision ID: a4c1e2f9b7d3
Revises: 983cf2b7d708
Create Date: 2026-11-22 04:00:00.000000
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = 'a4c1e2f9b7d3'
down_revision: str | None = '983cf2b7d708'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        'user_books',
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('ankibook_id', sa.Uuid(), nullable=False),
        sa.Column(
            'added_at',
            sa.DateTime(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ['user_id'], ['public.users.id'],
            name='fk_user_books_user_id_users_id', ondelete='CASCADE',
        ),
        sa.ForeignKeyConstraint(
            ['ankibook_id'], ['public.ankibooks.id'],
            name='fk_user_books_ankibook_id_ankibooks_id', ondelete='CASCADE',
        ),
        sa.PrimaryKeyConstraint('user_id', 'ankibook_id'),
        schema='public',
    )
    op.create_index(
        'user_books_idx_user_books_ankibook_id', 'user_books', ['ankibook_id'],
        unique=False, schema='public',
    )


def downgrade() -> None:
    op.drop_index('user_books_idx_user_books_ankibook_id', table_name='user_books', schema='public')
    op.drop_table('user_books', schema='public')
