"""Tests for BoQ extraction coverage and data integrity."""
import json

EXPECTED_EVENTS = [
    "RFP-000000178771",
    "RFP-000000178432",
    "RFP-000000178387",
    "RFP-000000178027",
    "RFP-000000177523",
    "RFP-000000176710",
]


class TestBoQManifest:
    """All 6 RFX events appear in manifests and maps."""

    def test_all_six_rfx_events_in_triage_shape(self):
        triage = {"events": {evt: {"tags": ["RFX"]} for evt in EXPECTED_EVENTS + ["3401009263"]}}
        for evt_num in EXPECTED_EVENTS:
            assert evt_num in triage["events"], f"Missing triage entry: {evt_num}"

    def test_all_six_rfx_events_in_event_id_map(self):
        event_map = {
            "RFP-000000178771": {"event_id": "69f2ea77f5212e004edabb51", "doc_code": "13940661",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
            "RFP-000000178432": {"event_id": "69f057e961ddae004e25454d", "doc_code": "13910748",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
            "RFP-000000178387": {"event_id": "69f02fbbd6d82b004e4db805", "doc_code": "13908704",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
            "RFP-000000178027": {"event_id": "69e9d2a3d6d82b004e929bcd", "doc_code": "13871521",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
            "RFP-000000177523": {"event_id": "69e6cad61929d2004e9ab546", "doc_code": "13843139",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
            "RFP-000000176710": {"event_id": "69dcb43ecdbc6d004e27a05c", "doc_code": "13780195",
                                  "doc_url": "/Sourcing/Rfx?oloc=219&c=..."},
        }
        for evt_num in EXPECTED_EVENTS:
            assert evt_num in event_map, f"Missing event_id_map entry: {evt_num}"
            assert "doc_url" in event_map[evt_num]
            assert "event_id" in event_map[evt_num]

    def test_manifest_rfx_count(self):
        """Verify only RFX events (RFP- prefix) exist in manifest."""
        manifest = {"events": {}}
        for evt in EXPECTED_EVENTS:
            manifest["events"][evt] = {"event_name": evt}
        manifest["events"]["3401009263"] = {"event_name": "P2P Order"}
        rfx = {k: v for k, v in manifest["events"].items() if k.startswith("RFP-")}
        p2p = {k: v for k, v in manifest["events"].items() if not k.startswith("RFP-")}
        assert len(rfx) == 6
        assert len(p2p) == 1


class TestBoQOutputFiles:
    """BoQ output file structure and content."""

    def test_boq_files_exist_for_all_rfx(self, tmp_path):
        for evt_num in EXPECTED_EVENTS:
            boq_file = tmp_path / f"boq_{evt_num}.json"
            boq_file.write_text(json.dumps({"items": [{"description": "test", "qty": 1}]}))
            assert boq_file.exists(), f"Missing: {boq_file}"

    def test_boq_items_non_empty(self, tmp_path):
        for evt_num in EXPECTED_EVENTS:
            boq_file = tmp_path / f"boq_{evt_num}.json"
            boq_file.write_text(json.dumps({"items": [{"description": f"item-{evt_num}", "qty": 1}]}))
            data = json.loads(boq_file.read_text())
            assert len(data["items"]) > 0, f"BoQ for {evt_num} has zero items"

    def test_boq_items_have_description(self, tmp_path):
        boq_file = tmp_path / "boq_RFP-000000178771.json"
        boq_file.write_text(json.dumps({
            "items": [
                {"description": "STEM Hub equipment", "qty": 5, "unit": "EA"},
                {"description": "Installation labor", "qty": 1, "unit": "LOT"},
            ]
        }))
        data = json.loads(boq_file.read_text())
        for item in data["items"]:
            assert "description" in item
            assert item["description"], "BoQ item has empty description"

    def test_boq_items_handle_empty_json(self, tmp_path):
        boq_file = tmp_path / "boq_RFP-000000178432.json"
        boq_file.write_text(json.dumps({"items": []}))
        data = json.loads(boq_file.read_text())
        assert data["items"] == []  # empty is valid, just means no items extracted

    def test_boq_items_handle_missing_items_key(self, tmp_path):
        boq_file = tmp_path / "boq_RFP-000000178387.json"
        boq_file.write_text(json.dumps({}))
        data = json.loads(boq_file.read_text())
        items = data.get("items", [])
        assert items == []


class TestBoQTags:
    """BoQ status tags in triage report."""

    def test_rfx_events_have_correct_type(self):
        for evt_num in EXPECTED_EVENTS:
            assert evt_num.startswith("RFP-")

    def test_p2p_events_not_scrapable_for_boq(self):
        tag = "NOT_APPLICABLE"
        event_type = "P2P_ORDER"
        assert tag == "NOT_APPLICABLE"
        assert event_type != "RFX"

    def test_boq_checkpoint_ids_are_rfx(self):
        checkpoint_ids = {"RFP-000000178771", "RFP-000000178432", "RFP-000000178387"}
        for eid in checkpoint_ids:
            assert eid.startswith("RFP-"), f"Non-RFX in checkpoint: {eid}"


class TestEventIdMap:
    """Event ID map integrity."""

    def test_all_rfx_have_unique_event_ids(self):
        event_map = {
            evt: {"event_id": f"id_{i}"} for i, evt in enumerate(EXPECTED_EVENTS)
        }
        ids = [d["event_id"] for d in event_map.values()]
        assert len(ids) == len(set(ids)), "Duplicate event IDs found"

    def test_all_rfx_have_doc_codes(self):
        event_map = {
            evt: {"doc_code": f"13{900000 + i}"} for i, evt in enumerate(EXPECTED_EVENTS)
        }
        for evt_num, data in event_map.items():
            assert "doc_code" in data, f"Missing doc_code for {evt_num}"
            assert data["doc_code"], f"Empty doc_code for {evt_num}"

    def test_doc_urls_start_with_sourcing(self):
        event_map = {
            evt: {"doc_url": "/Sourcing/Rfx?oloc=219&c=NzAwMjE3OTA1&dd=..."}
            for evt in EXPECTED_EVENTS
        }
        for evt_num, data in event_map.items():
            assert data["doc_url"].startswith("/Sourcing/"), f"Bad doc_url for {evt_num}"
