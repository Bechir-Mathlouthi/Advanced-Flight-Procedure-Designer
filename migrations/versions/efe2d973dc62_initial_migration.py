"""Initial migration

Revision ID: efe2d973dc62
Revises: 
Create Date: 2024-12-05 11:25:14.216565

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'efe2d973dc62'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('flight_procedures',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('airport_icao', sa.String(length=4), nullable=False),
    sa.Column('procedure_type', sa.Enum('SID', 'STAR', 'APPROACH', name='proceduretype'), nullable=False),
    sa.Column('navigation_type', sa.Enum('RNAV', 'RNP', 'ILS', 'VOR', 'NDB', name='navigationtype'), nullable=False),
    sa.Column('minimum_altitude', sa.Float(), nullable=True),
    sa.Column('maximum_altitude', sa.Float(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=True),
    sa.Column('updated_at', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=128), nullable=True),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('email'),
    sa.UniqueConstraint('username')
    )
    op.create_table('obstacle_assessments',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('procedure_id', sa.Integer(), nullable=False),
    sa.Column('obstacle_name', sa.String(length=100), nullable=True),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('height', sa.Float(), nullable=False),
    sa.Column('clearance', sa.Float(), nullable=False),
    sa.Column('assessment_date', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['procedure_id'], ['flight_procedures.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_table('waypoints',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('procedure_id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=10), nullable=False),
    sa.Column('latitude', sa.Float(), nullable=False),
    sa.Column('longitude', sa.Float(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('altitude_constraint', sa.Float(), nullable=True),
    sa.Column('speed_constraint', sa.Float(), nullable=True),
    sa.ForeignKeyConstraint(['procedure_id'], ['flight_procedures.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('waypoints')
    op.drop_table('obstacle_assessments')
    op.drop_table('users')
    op.drop_table('flight_procedures')
    # ### end Alembic commands ###
