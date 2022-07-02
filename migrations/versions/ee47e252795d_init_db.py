"""init db

Revision ID: ee47e252795d
Revises:
Create Date: 2022-06-17 15:36:46.968440

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "ee47e252795d"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "models",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("graph_id", sa.String(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "template_library",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "template",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("_head", sa.String(), nullable=False),
        sa.Column("body_id", sa.String(), nullable=True),
        sa.Column("template_library_id", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["template_library_id"],
            ["template_library.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "name",
            "template_library_id",
            name="name_template_library_unique_constraint",
        ),
    )
    op.create_table(
        "deps_association_table",
        sa.Column("dependant_id", sa.Integer(), nullable=False),
        sa.Column("dependee_id", sa.Integer(), nullable=False),
        sa.Column("args", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(
            ["dependant_id"],
            ["template.id"],
        ),
        sa.ForeignKeyConstraint(
            ["dependee_id"],
            ["template.id"],
        ),
        sa.PrimaryKeyConstraint("dependant_id", "dependee_id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("deps_association_table")
    op.drop_table("template")
    op.drop_table("template_library")
    op.drop_table("models")
    # ### end Alembic commands ###