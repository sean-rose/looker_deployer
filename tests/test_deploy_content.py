import pytest
import deploy_content
import os
import networkx
from looker_sdk import models

WALK_TUPLE = [("foo", ["bar", "baz"], ["Space1", "Look1", "Dashboard1", "Dinosaur"])]


class MockSDK:

    def search_spaces(self, name):
        return [models.Space(name=name, id=42, parent_id=2)]

    def create_space(self, space):
        space.id = 42
        return space


def test_get_space_ids_from_name_shared():
    sdk = MockSDK()
    id_list = deploy_content.get_space_ids_from_name("Shared", sdk)
    assert id_list == [1]


def test_get_space_ids_from_name_not_shared():
    sdk = MockSDK()
    id_list = deploy_content.get_space_ids_from_name("foo", sdk)
    assert id_list == [42]


def test_create_or_return_space_one_found(mocker):
    mocker.patch("deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = [42]
    target_id = deploy_content.create_or_return_space("foo", "bar", "baz")
    assert target_id == 42


def test_create_or_return_space_multi_found(mocker):
    mocker.patch("deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = [42, 13]
    with pytest.raises(AssertionError):
        deploy_content.create_or_return_space("foo", "bar", "baz")


def test_create_or_return_space_none_found(mocker):
    mocker.patch("deploy_content.get_space_ids_from_name")
    deploy_content.get_space_ids_from_name.return_value = []

    sdk = MockSDK()

    target_id = deploy_content.create_or_return_space("foo", 2, sdk)
    assert target_id == 42


def test_build_directory_graph_add_edge_call(mocker):
    mocker.patch("networkx.DiGraph.add_edges_from")
    mocker.patch("os.walk")
    os.walk.return_value = WALK_TUPLE
    deploy_content.build_directory_graph("foo")
    networkx.DiGraph.add_edges_from.assert_called_with([("foo", "bar"), ("foo", "baz")])


def test_build_directory_graph_add_node_call(mocker):
    mocker.patch("networkx.DiGraph.add_edges_from")
    mocker.patch("networkx.DiGraph.add_node")
    mocker.patch("os.walk")
    os.walk.return_value = WALK_TUPLE
    deploy_content.build_directory_graph("foo")
    networkx.DiGraph.add_node.assert_called_with(
        "foo",
        space="Space1",
        looks=["Look1"],
        dashboards=["Dashboard1"],
        path="foo"
    )


def test_parse_root():
    content = "foo/Shared/bar/"
    root_dir = deploy_content.parse_root(content)
    assert root_dir == "foo/Shared"


def test_parse_content_path():
    path = "foo/bar/Shared/spam/eggs.json"
    ref = deploy_content.parse_content_path(path)
    assert ref == {"content_space": "spam", "content_file": "eggs.json"}


def test_deploy_content(mocker):
    mocker.patch("deploy_content.parse_content_path")
    mocker.patch("deploy_content.deploy_space")
    mocker.patch("deploy_content.import_content")
    mocker.patch("networkx.shortest_path")

    deploy_content.parse_content_path.return_value = {"content_space": "foo"}
    deploy_content.deploy_space.return_value = 42
    networkx.shortest_path.return_value = ["taco", "foo"]
    deploy_content.deploy_content("dashboard", ["spam"], "dg", "root_dir", "sdk", "host")
    deploy_content.import_content.assert_called_with("dashboard", "spam", 42, "host")