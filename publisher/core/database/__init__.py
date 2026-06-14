"""
Database layer for Pipeline Publisher.

Architecture (Level 2 — DCC session singleton):
- DatabaseService: connection pool singleton, initialized once per DCC session
- PublishRepository: data access for publish operations

All modules share the same pool via DatabaseService class methods.
"""
