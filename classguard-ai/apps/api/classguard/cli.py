"""Trusted local administration alongside the authenticated onboarding API.

Run this CLI only as a trusted operator with direct database access. It is not
an unauthenticated HTTP endpoint and does not create Supabase identities.
"""

import argparse
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import Base, get_engine
from .models import Classroom, Enrollment, Institution, Membership


def provision(args: argparse.Namespace) -> None:
    with Session(get_engine()) as database:
        if args.institution_id:
            institution = database.get(Institution, args.institution_id)
            if institution is None:
                raise ValueError("Institution does not exist")
        else:
            institution = Institution(name=args.institution_name.strip())
            if not institution.name:
                raise ValueError("Institution name must not be empty")
            database.add(institution)
            database.flush()
        membership = database.get(Membership, (institution.id, args.user_id))
        if membership is None:
            membership = Membership(institution_id=institution.id, user_id=args.user_id, role=args.role)
            database.add(membership)
        else:
            membership.role = args.role
            membership.active = True
        database.commit()
        print(f"Institution ID: {institution.id}")
        print(f"Membership role: {membership.role}")


def enroll(args: argparse.Namespace) -> None:
    with Session(get_engine()) as database:
        membership = database.get(Membership, (args.institution_id, args.user_id))
        classroom = database.scalar(
            select(Classroom).where(
                Classroom.id == args.class_id,
                Classroom.institution_id == args.institution_id,
            )
        )
        if membership is None or not membership.active or membership.role != "student":
            raise ValueError("An active student membership in this institution is required")
        if classroom is None:
            raise ValueError("Classroom does not belong to this institution")
        enrollment_id = (args.class_id, args.institution_id, args.user_id)
        if database.get(Enrollment, enrollment_id) is None:
            database.add(Enrollment(
                classroom_id=args.class_id,
                institution_id=args.institution_id,
                user_id=args.user_id,
            ))
            database.commit()
        print("Student enrolled")


def main() -> None:
    parser = argparse.ArgumentParser(description="ClassGuard AI local administration")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("init-db", help="Create missing foundation and onboarding tables for local development")

    provision_parser = commands.add_parser("provision", help="Assign an existing Supabase user a membership")
    institution = provision_parser.add_mutually_exclusive_group(required=True)
    institution.add_argument("--institution-id", type=UUID)
    institution.add_argument("--institution-name")
    provision_parser.add_argument("--user-id", type=UUID, required=True)
    provision_parser.add_argument("--role", choices=["admin", "teacher", "student"], required=True)

    enrollment_parser = commands.add_parser("enroll", help="Enroll an existing student into a class")
    enrollment_parser.add_argument("--institution-id", type=UUID, required=True)
    enrollment_parser.add_argument("--class-id", type=UUID, required=True)
    enrollment_parser.add_argument("--user-id", type=UUID, required=True)

    args = parser.parse_args()
    try:
        if args.command == "init-db":
            Base.metadata.create_all(get_engine())
            print("Development database initialized, including onboarding tables. Existing tables are unchanged; use migrations for schema changes.")
        elif args.command == "provision":
            provision(args)
        elif args.command == "enroll":
            enroll(args)
    except ValueError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
