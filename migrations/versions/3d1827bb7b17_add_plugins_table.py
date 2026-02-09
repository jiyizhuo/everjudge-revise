"""add_plugins_table

Revision ID: 3d1827bb7b17
Revises: 3d1827bb7b16
Create Date: 2026-02-09 12:30:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '3d1827bb7b17'
down_revision = '3d1827bb7b16'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'plugins',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('version', sa.String(50), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('author', sa.String(200), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=False, default=False),
        sa.Column('installed_at', sa.DateTime(), nullable=True),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.Column('hooks', sa.Text(), nullable=True),
        sa.Column('config', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.Index('ix_plugins_name', 'name')
    )


def downgrade():
    op.drop_table('plugins')
