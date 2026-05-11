"""Tests for --datatype-converter CLI option wiring."""

from __future__ import annotations


from katalogue_cli.cli.main import cli


def _options(mock_client):
    return mock_client.get.call_args.args[1]


class TestDatatypeConverterOption:
    def test_dataset_get_passes_datatype_converter(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result(
            {
                "dataset_id": 1,
                "fields": [
                    {
                        "field_name": "amount",
                        "datatype_fullname": "DECIMAL(10,2)",
                        "datatype_converted": "DECIMAL(10,2)",
                    }
                ],
            },
            "json",
        )
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "dataset",
                "get",
                "1",
                "--datatype-converter",
                "sqlserver-to-databricks",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).datatype_converter == "sqlserver-to-databricks"

    def test_system_get_passes_datatype_converter(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result({"system_id": 1}, "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "system",
                "get",
                "1",
                "--datatype-converter",
                "db2-to-databricks",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).datatype_converter == "db2-to-databricks"

    def test_datatype_converter_defaults_none(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result({"dataset_id": 1}, "json")
        result = runner.invoke(
            cli, [*cli_auth, "dataset", "get", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert _options(mock_client).datatype_converter is None

    def test_datasource_export_passes_datatype_converter(
        self, runner, cli_auth, mock_client, catalog_result
    ):
        mock_client.get.return_value = catalog_result({"datasource_id": 5}, "json")
        result = runner.invoke(
            cli,
            [
                *cli_auth,
                "datasource",
                "export",
                "5",
                "--datatype-converter",
                "sqlserver-to-databricks",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert _options(mock_client).datatype_converter == "sqlserver-to-databricks"
