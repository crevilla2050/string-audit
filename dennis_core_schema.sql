
-- ============================================================
-- Dennis Forge Core Database Schema
-- Engine: MySQL 8+
-- Charset: utf8mb4
-- UUID storage: BINARY(16)
-- ============================================================

CREATE DATABASE IF NOT EXISTS db_dennis_core
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE db_dennis_core;

-- USERS
CREATE TABLE tbl_users (
  uuid_user BINARY(16) NOT NULL,
  chr_username VARCHAR(128) NOT NULL,
  chr_email_hash CHAR(64) NOT NULL,
  chr_password_hash CHAR(255) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  bit_deleted TINYINT(1) DEFAULT 0,
  PRIMARY KEY (uuid_user),
  UNIQUE KEY uk_username (chr_username)
) ENGINE=InnoDB;

CREATE TABLE tbl_password_history (
  uuid_password BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_password_hash CHAR(255) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_password),
  INDEX idx_user (uuid_user)
) ENGINE=InnoDB;

-- ORGANIZATIONS
CREATE TABLE tbl_organizations (
  uuid_organization BINARY(16) NOT NULL,
  chr_name VARCHAR(255) NOT NULL,
  chr_subscription_tier VARCHAR(32) DEFAULT 'free',
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  bit_deleted TINYINT(1) DEFAULT 0,
  PRIMARY KEY (uuid_organization)
) ENGINE=InnoDB;

CREATE TABLE tbl_organization_members (
  uuid_org_member BINARY(16) NOT NULL,
  uuid_organization BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_role VARCHAR(64),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_org_member),
  INDEX idx_org (uuid_organization),
  INDEX idx_user (uuid_user)
) ENGINE=InnoDB;

-- TEAMS
CREATE TABLE tbl_teams (
  uuid_team BINARY(16) NOT NULL,
  uuid_organization BINARY(16) NOT NULL,
  chr_name VARCHAR(255) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_team),
  INDEX idx_org (uuid_organization)
) ENGINE=InnoDB;

CREATE TABLE tbl_team_members (
  uuid_team_member BINARY(16) NOT NULL,
  uuid_team BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_role VARCHAR(64),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_team_member),
  INDEX idx_team (uuid_team),
  INDEX idx_user (uuid_user)
) ENGINE=InnoDB;

CREATE TABLE tbl_team_projects (
  uuid_team_project BINARY(16) NOT NULL,
  uuid_team BINARY(16) NOT NULL,
  uuid_project BINARY(16) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_team_project),
  INDEX idx_team (uuid_team),
  INDEX idx_project (uuid_project)
) ENGINE=InnoDB;

-- WORKSPACES
CREATE TABLE tbl_workspaces (
  uuid_workspace BINARY(16) NOT NULL,
  uuid_organization BINARY(16) NOT NULL,
  chr_name VARCHAR(255) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_workspace),
  INDEX idx_org (uuid_organization)
) ENGINE=InnoDB;

CREATE TABLE tbl_workspace_members (
  uuid_workspace_member BINARY(16) NOT NULL,
  uuid_workspace BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_role VARCHAR(64),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_workspace_member),
  INDEX idx_workspace (uuid_workspace),
  INDEX idx_user (uuid_user)
) ENGINE=InnoDB;

-- PROJECTS
CREATE TABLE tbl_projects (
  uuid_project BINARY(16) NOT NULL,
  uuid_workspace BINARY(16) NOT NULL,
  chr_name VARCHAR(255) NOT NULL,
  txt_description TEXT,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  bit_deleted TINYINT(1) DEFAULT 0,
  PRIMARY KEY (uuid_project),
  INDEX idx_workspace (uuid_workspace)
) ENGINE=InnoDB;

-- ARTIFACT OBJECTS
CREATE TABLE tbl_artifact_objects (
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_artifact_hash CHAR(64) NOT NULL,
  chr_parent_hash CHAR(64),
  chr_chain_status VARCHAR(32) DEFAULT 'valid',
  ts_artifact_created TIMESTAMP NULL,
  chr_payload_hash CHAR(64),
  chr_manifest_hash CHAR(64),
  int_size_bytes BIGINT,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  bit_deleted TINYINT(1) DEFAULT 0,
  PRIMARY KEY (uuid_artifact_object),
  UNIQUE KEY uk_hash (chr_artifact_hash),
  INDEX idx_parent (chr_parent_hash)
) ENGINE=InnoDB;

CREATE TABLE tbl_artifacts (
  uuid_artifact BINARY(16) NOT NULL,
  uuid_project BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_name VARCHAR(255),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_artifact),
  INDEX idx_project (uuid_project)
) ENGINE=InnoDB;

-- STORAGE
CREATE TABLE tbl_artifact_storage (
  uuid_storage BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_storage_backend VARCHAR(32) NOT NULL,
  chr_storage_uri VARCHAR(1024) NOT NULL,
  chr_region VARCHAR(64),
  int_size_bytes BIGINT,
  bit_primary TINYINT(1) DEFAULT 1,
  ts_uploaded TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_storage),
  INDEX idx_artifact (uuid_artifact_object)
) ENGINE=InnoDB;

-- SIGNATURES
CREATE TABLE tbl_artifact_signatures (
  uuid_signature BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_key_fingerprint CHAR(64) NOT NULL,
  chr_algorithm VARCHAR(32),
  chr_signature TEXT,
  ts_signed TIMESTAMP,
  PRIMARY KEY (uuid_signature),
  INDEX idx_artifact (uuid_artifact_object)
) ENGINE=InnoDB;

CREATE TABLE tbl_user_keys (
  uuid_user_key BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_public_key TEXT NOT NULL,
  chr_key_fingerprint CHAR(64) NOT NULL,
  chr_algorithm VARCHAR(32),
  chr_key_label VARCHAR(255),
  bit_primary TINYINT(1) DEFAULT 0,
  bit_revoked TINYINT(1) DEFAULT 0,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ts_revoked TIMESTAMP NULL,
  PRIMARY KEY (uuid_user_key),
  UNIQUE KEY uk_fingerprint (chr_key_fingerprint),
  INDEX idx_user (uuid_user)
) ENGINE=InnoDB;

-- REVIEWS
CREATE TABLE tbl_review_targets (
  uuid_target BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_target)
) ENGINE=InnoDB;

CREATE TABLE tbl_reviews (
  uuid_review BINARY(16) NOT NULL,
  uuid_target BINARY(16) NOT NULL,
  uuid_user BINARY(16),
  chr_status VARCHAR(32),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_review),
  INDEX idx_target (uuid_target)
) ENGINE=InnoDB;

CREATE TABLE tbl_review_comments (
  uuid_comment BINARY(16) NOT NULL,
  uuid_review BINARY(16) NOT NULL,
  uuid_user BINARY(16),
  uuid_parent_comment BINARY(16),
  txt_comment TEXT,
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_comment),
  INDEX idx_review (uuid_review)
) ENGINE=InnoDB;

CREATE TABLE tbl_review_attestations (
  uuid_attestation BINARY(16) NOT NULL,
  uuid_review BINARY(16) NOT NULL,
  uuid_user BINARY(16) NOT NULL,
  chr_decision VARCHAR(32),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_attestation),
  INDEX idx_review (uuid_review)
) ENGINE=InnoDB;

-- REGISTRIES
CREATE TABLE tbl_registries (
  uuid_registry BINARY(16) NOT NULL,
  uuid_organization BINARY(16),
  chr_name VARCHAR(255),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_registry)
) ENGINE=InnoDB;

CREATE TABLE tbl_registry_artifacts (
  uuid_registry_artifact BINARY(16) NOT NULL,
  uuid_registry BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  ts_added TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_registry_artifact),
  INDEX idx_registry (uuid_registry)
) ENGINE=InnoDB;

-- FEEDS
CREATE TABLE tbl_artifact_feeds (
  uuid_feed BINARY(16) NOT NULL,
  uuid_organization BINARY(16),
  chr_name VARCHAR(255),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_feed)
) ENGINE=InnoDB;

CREATE TABLE tbl_feed_artifacts (
  uuid_feed_artifact BINARY(16) NOT NULL,
  uuid_feed BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  ts_published TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_feed_artifact),
  INDEX idx_feed (uuid_feed)
) ENGINE=InnoDB;

-- POLICY RULES
CREATE TABLE tbl_policy_rules (
  uuid_policy BINARY(16) NOT NULL,
  uuid_organization BINARY(16),
  uuid_workspace BINARY(16),
  uuid_project BINARY(16),
  chr_operation VARCHAR(64) NOT NULL,
  bit_require_signature TINYINT(1) DEFAULT 0,
  bit_require_active_key TINYINT(1) DEFAULT 0,
  int_min_signatures INT DEFAULT 0,
  int_required_reviewers INT DEFAULT 0,
  uuid_required_team BINARY(16),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  ts_updated TIMESTAMP NULL,
  bit_deleted TINYINT(1) DEFAULT 0,
  PRIMARY KEY (uuid_policy)
) ENGINE=InnoDB;

-- AUDIT CHAIN
CREATE TABLE tbl_audit_logs (
  uuid_audit BINARY(16) NOT NULL,
  chr_event_type VARCHAR(64),
  uuid_actor BINARY(16),
  uuid_target BINARY(16),
  txt_event_data JSON,
  chr_prev_hash CHAR(64),
  chr_hash CHAR(64),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_audit),
  INDEX idx_actor (uuid_actor)
) ENGINE=InnoDB;

-- INGESTION
CREATE TABLE tbl_ingestion_jobs (
  uuid_job BINARY(16) NOT NULL,
  chr_source VARCHAR(255),
  chr_status VARCHAR(32),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_job)
) ENGINE=InnoDB;

CREATE TABLE tbl_ingestion_events (
  uuid_event BINARY(16) NOT NULL,
  uuid_job BINARY(16),
  chr_event VARCHAR(255),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_event),
  INDEX idx_job (uuid_job)
) ENGINE=InnoDB;

CREATE TABLE tbl_artifact_metadata (
  uuid_metadata BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_name VARCHAR(255),
  chr_summary VARCHAR(512),
  txt_description TEXT,
  chr_author VARCHAR(255),
  chr_license VARCHAR(64),
  chr_category VARCHAR(128),
  ts_created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (uuid_metadata),
  INDEX idx_artifact (uuid_artifact_object)
) ENGINE=InnoDB;

CREATE TABLE tbl_artifact_tags (
  uuid_tag BINARY(16) NOT NULL,
  uuid_artifact_object BINARY(16) NOT NULL,
  chr_tag VARCHAR(64),
  PRIMARY KEY (uuid_tag),
  INDEX idx_tag (chr_tag)
) ENGINE=InnoDB;