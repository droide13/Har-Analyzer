import json
from typing import Any, Dict, List, Optional, Set, TypedDict


# --- Type Definitions for Strict Typing ---
class OutputValueItem(TypedDict):
    value: str
    appearances: int


class OutputIdentifier(TypedDict):
    key: str
    total_appearances: int
    domains: List[str]
    values: List[OutputValueItem]


class CondensedHARData(TypedDict):
    cookies: List[OutputIdentifier]
    params: List[OutputIdentifier]


# --- Core Logic Functions ---
def extract_identifiers(
    input_data: Dict[str, Any],
    min_appearances: int = 10,
    max_unique_values: int = 5,
) -> CondensedHARData:
    """Parses HAR dictionary data to extract stable identifiers based on thresholds."""
    result: CondensedHARData = {"cookies": [], "params": []}
    target_sections = ["cookies", "params"]

    for section in target_sections:
        if section not in input_data:
            continue

        for item in input_data[section]:
            key: str = item.get("key", "")
            total_appearances: int = item.get("appearances", 0)
            values_list: List[Dict[str, Any]] = item.get("values", [])

            unique_values_count = len(values_list)

            if total_appearances >= min_appearances and unique_values_count <= max_unique_values:
                unique_domains: Set[str] = set()
                extracted_values: List[OutputValueItem] = []

                for val_entry in values_list:
                    extracted_values.append(
                        {
                            "value": val_entry.get("value", ""),
                            "appearances": val_entry.get("appearances", 0),
                        }
                    )

                    for request in val_entry.get("requests", []):
                        domain = request.get("domain")
                        if domain:
                            unique_domains.add(domain)

                identifier_summary: OutputIdentifier = {
                    "key": key,
                    "total_appearances": total_appearances,
                    "domains": sorted(list(unique_domains)),
                    "values": extracted_values,
                }

                result[section].append(identifier_summary)  # type: ignore

    return result


def process_har_file(
    input_file_path: str,
    output_file_path: Optional[str] = None,
    min_appearances: int = 10,
    max_unique_values: int = 5,
) -> CondensedHARData:
    """Reads a JSON file from a string path, extracts identifiers, and optionally

    saves the condensed JSON results to a target path.
    """
    # Open and safely read the source file
    with open(input_file_path, "r", encoding="utf-8") as file:
        raw_data: Dict[str, Any] = json.load(file)

    # Process the data using the core engine
    condensed_data = extract_identifiers(
        input_data=raw_data,
        min_appearances=min_appearances,
        max_unique_values=max_unique_values,
    )

    # Optional: Write directly to an output path if provided
    if output_file_path:
        with open(output_file_path, "w", encoding="utf-8") as file:
            json.dump(condensed_data, file, indent=2)

    return condensed_data


# --- Example Usage ---
if __name__ == "__main__":
    # Define your file string paths
    SOURCE_PATH = "data/manual/slickdeals.out.json"
    DESTINATION_PATH = "data/manual/slickdels.output_identifiers.json"

    try:

        processed_json = process_har_file(
            input_file_path=SOURCE_PATH,
            output_file_path=DESTINATION_PATH,
            min_appearances=15,
            max_unique_values=3,
        )
        print("Processing complete. Check your destination path.")

        pass
    except FileNotFoundError as e:
        print(f"Error: Could not locate the file specified. {e}")
