BEGIN TRANSACTION;

-- =====================================================
-- ROLES (minimal local permission model)
-- =====================================================
INSERT OR IGNORE INTO roles (id_role, chr_name) VALUES
(X'00000000000070008000000000000001', 'owner'),
(X'00000000000070008000000000000002', 'collaborator'),
(X'00000000000070008000000000000003', 'viewer');

-- =====================================================
-- KEY TYPES (crypto agility)
-- =====================================================
INSERT OR IGNORE INTO key_types (id_key_type, chr_name, chr_description) VALUES
(X'00000000000070008000000000000101', 'ed25519', 'Default modern signing'),
(X'00000000000070008000000000000102', 'rsa4096', 'Legacy compatibility'),
(X'00000000000070008000000000000103', 'pq_experimental', 'Reserved for post-quantum algorithms');

-- =====================================================
-- EVENT TYPES (local history semantics)
-- =====================================================
INSERT OR IGNORE INTO event_types (id_event_type, chr_name) VALUES
(X'00000000000070008000000000000401', 'identity_created'),
(X'00000000000070008000000000000402', 'key_generated'),
(X'00000000000070008000000000000403', 'plan_created'),
(X'00000000000070008000000000000404', 'plan_updated'),
(X'00000000000070008000000000000405', 'plan_signed'),
(X'00000000000070008000000000000406', 'bundle_created'),
(X'00000000000070008000000000000407', 'bundle_verified'),
(X'00000000000070008000000000000408', 'workspace_created'),
(X'00000000000070008000000000000409', 'workspace_member_added'),
(X'0000000000007000800000000000040A', 'installation_initialized');

COMMIT;
