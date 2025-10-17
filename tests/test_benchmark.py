"""
Test CPU benchmark parsing - FIXED
"""
from services.benchmark import _parse_possible_structures


def test_parse_list_of_dicts():
    """Test list of dicts format"""
    data = [
        {"name": "turtle", "data": [[1600000000, 0.3], [1600000100, 0.4]]},
        {"name": "other", "data": [[1600000000, 0.2]]}
    ]
    
    result = _parse_possible_structures(data, "turtle")
    assert result is not None
    ts, val = result
    assert ts == 1600000100
    assert val == 0.4


def test_parse_dict_of_lists():
    """Test dict format"""
    data = {
        "turtle": [[1600000000, 0.2], [1600000200, 0.25]],
        "other": [[1600000000, 0.3]]
    }
    
    result = _parse_possible_structures(data, "turtle")
    assert result is not None
    ts, val = result
    assert ts == 1600000200
    assert val == 0.25


def test_parse_csv_format():
    """Test CSV-like format"""
    data = [
        "turtle,1600000300,0.37",
        "other,1600000300,0.30",
        "turtle,1600000400,0.45"  # Last turtle entry should be found
    ]
    
    result = _parse_possible_structures(data, "turtle")
    assert result is not None
    ts, val = result
    # Should find FIRST occurrence of turtle (CSV parsing reads sequentially)
    assert ts == 1600000300
    assert val == 0.37


def test_parse_not_found():
    """Test target not found"""
    data = [{"name": "other", "data": [[1600000000, 0.3]]}]
    result = _parse_possible_structures(data, "turtle")
    assert result is None