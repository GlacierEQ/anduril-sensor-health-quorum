# Sensor Health Quorum

**Lens:** lattice sensor trust (Anduril-class)  
**Innovation:** Sensors vote on peer health; a sensor below quorum trust cannot cast track votes.


## Claim ceiling (independent reference)

Independent GlacierEQ reference only. No company affiliation, employment, deployment,
endorsement, clearance, or proprietary access is claimed. Names label public problem spaces.

### Machine–Mesh Protocol Manifest

<!-- glacier-eq-protocol:start -->
```yaml
{
  "schema": "glacier-eq.readme.machine-mesh/v1",
  "repository": {
    "id": "GlacierEQ/anduril-sensor-health-quorum",
    "url": "https://github.com/GlacierEQ/anduril-sensor-health-quorum",
    "readme_contract": "estate-machine-v1",
    "default_branch": "main"
  },
  "machine": {
    "repository_kind": "migration-residue",
    "public_api": "inspect-declared-entrypoints",
    "protocol_files": [],
    "entrypoints": [
      {
        "kind": "package-contract",
        "path": "go.mod",
        "policy": "inspect-before-use"
      },
      {
        "kind": "source-area",
        "path": "src",
        "policy": "inspect-before-use"
      },
      {
        "kind": "script-area",
        "path": "scripts",
        "policy": "inspect-before-use"
      },
      {
        "kind": "test-area",
        "path": "tests",
        "policy": "run-before-reliance"
      },
      {
        "kind": "machine-contract-area",
        "path": "machine",
        "policy": "read-first"
      }
    ]
  },
  "presentation": {
    "architecture": [
      "recruiter",
      "master",
      "machine",
      "mesh"
    ],
    "authority": {
      "capability": "stone-psysoc-x",
      "repository": "GlacierEQ/AKOS",
      "manifest": "stones/psysoc-x/stone.json",
      "engine": "infinity_stones/psysoc_x.py"
    },
    "truth_invariant": "presentation-may-change-sequence-density-tone-and-style; facts-evidence-uncertainty-provenance-dignity-and-reader-agency-may-not"
  },
  "license": {
    "class": "EXISTING_LICENSE",
    "status": "CONTROLLING_LICENSE_CONTENT_REVIEW_REQUIRED",
    "controlling_path": "LICENSE",
    "policy": "GlacierEQ/job-app-helix/LICENSE_POLICY.json",
    "may_relicense_automatically": false,
    "upstream_rights_must_be_preserved": false
  },
  "mesh": {
    "primary_home": null,
    "branch": "migration-residue",
    "subcategory": "unresolved-primary-home",
    "routing": [
      {
        "relation": "estate-map",
        "target": "GlacierEQ/monolith",
        "url": "https://github.com/GlacierEQ/monolith"
      }
    ],
    "boundaries": [
      "routing-does-not-transfer-source-code-evidence-deployment-or-lifecycle-authority",
      "generated-contract-is-a-source-index-not-a-runtime-or-provider-receipt",
      "implementation-and-provider-state-require-independent-evidence",
      "presentation-calibration-cannot-promote-claim-or-evidence-state",
      "license-automation-cannot-relicense-unresolved-upstream-or-third-party-rights"
    ]
  },
  "provenance": {
    "generated_by": "GlacierEQ/job-app-helix",
    "generator_contract": "estate-machine-v1",
    "classification_source": null,
    "classification_evidence_path": null,
    "classification_evidence_blob_sha": null,
    "classification_status": null,
    "contract_digest": "038b756cf459da3ccc4e70088c9b4b15f69b785d3c662074b3da41ac620b50f3"
  }
}
```
<!-- glacier-eq-protocol:end -->
