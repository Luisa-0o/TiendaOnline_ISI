"""Comandos: flask init-db | flask create-admin | flask seed-demo"""
import click
from flask import Flask
from sqlalchemy.exc import SQLAlchemyError


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    def init_db():
        """Crea las tablas en una base nueva y la marca como migrada."""
        from app import init_schema
        click.echo("Esquema creado." if init_schema(app) else "La base de datos ya tiene tablas; no se modificó.")

    @app.cli.command("create-admin")
    @click.option("--username", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
    def create_admin(username, email, password):
        """Crea un administrador (o promueve a un usuario existente con ese correo)."""
        from extensions import db
        from models import ROLE_ADMIN
        from services.users import AccountError, AccountService
        service = AccountService(db.session)
        existing = service.find_by_email(email)
        try:
            if existing:
                existing.role = ROLE_ADMIN
                db.session.commit()
                click.echo(f"{existing.email} ahora es administrador.")
            else:
                user = service.admin_create(username, email, password, ROLE_ADMIN)
                click.echo(f"Administrador creado: {user.email}")
        except (AccountError, SQLAlchemyError) as exc:
            db.session.rollback()
            raise click.ClickException(str(exc))
