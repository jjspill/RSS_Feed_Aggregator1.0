import xml.etree.ElementTree as ET
from dateutil.parser import parse
from datetime import datetime, timezone
import xml.dom.minidom
import re
import os


def is_valid_atom_id(atom_id):
    """
    Checks if the atom_id is a valid URI or URN.
    """
    uri_pattern = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*://.*$")
    urn_pattern = re.compile(r"^urn:[a-zA-Z0-9][a-zA-Z0-9-]{0,31}:.*$")

    return (
        uri_pattern.match(atom_id) is not None
        or urn_pattern.match(atom_id) is not None
    )


def is_atom_time(date_str):
    """
    Checks if the date_str is a valid RFC-3339 date-time string.
    """
    try:
        datetime.fromisoformat(date_str)
        return True
    except ValueError:
        return False


def custom_timezone_parser(time_string):
    """
    Attempts to parse the time_string with timezone info.
    """
    tzinfos = {"UT": 0}
    return parse(time_string, tzinfos=tzinfos)


def create_xml(entries, feed_data):
    """
    Create XML from entries and feed_data using ElementTree.
    """

    root = ET.Element("feed", xmlns="http://www.w3.org/2005/Atom")

    ET.SubElement(root, "title").text = feed_data["title"]
    ET.SubElement(root, "id").text = feed_data["id"]
    ET.SubElement(root, "updated").text = feed_data["updated"]

    for entry in entries:
        process_entry(root, entry, feed_data)

    xml_string = ET.tostring(
        root, encoding=feed_data["encoding"], method="xml"
    )
    dom = xml.dom.minidom.parseString(xml_string)
    return dom.toprettyxml(indent="  ", encoding=feed_data["encoding"]).decode(
        feed_data["encoding"]
    )


def process_entry(root, entry, feed_data):
    """
    Process each entry and add to root.
    Required fields are title, author, id, updated, and link.
    """

    entry_element = ET.SubElement(root, "entry")
    handlers = {
        "title": process_title,
        "published": process_published,
        "updated": process_updated,
        "id": process_id,
        "summary": process_summary,
        "enclosures": process_enclosures,
        "tags": process_tags,
        "link": process_link,
        "author": process_author,
    }

    for _, handler in handlers.items():
        handler(entry_element, entry, feed_data)


# Required
def process_title(entry_element, entry, feed_data):
    ET.SubElement(entry_element, "title").text = entry.get("title", "No title")


# Optional
def process_published(entry_element, entry, feed_data):
    published = entry.get("published", feed_data["updated"])
    if not is_atom_time(published):
        # Change time format to ISO 8601
        try:
            parsed_date = custom_timezone_parser(published)
            published = parsed_date.replace(tzinfo=timezone.utc).isoformat()

        except Exception as e:
            # Not necessary for entry to have published date
            print(f"==== Error parsing published date: {e}")

    ET.SubElement(entry_element, "published").text = published


# Required
def process_updated(entry_element, entry, feed_data):
    updated = entry.get("updated", feed_data["updated"])
    if not is_atom_time(updated):
        # Change time format to ISO 8601
        parsed_date = custom_timezone_parser(updated)
        updated = parsed_date.replace(tzinfo=timezone.utc).isoformat()

    ET.SubElement(entry_element, "updated").text = updated


# Required
def process_id(entry_element, entry, feed_data):
    # Check if id exists and is a valid URI or URN
    id_value = entry.get("id", f"urn:tag:{entry['id']}")
    if not is_valid_atom_id(id_value):
        # Change id format to URN
        id_value = f"urn:tag:{entry['id']}"

    ET.SubElement(entry_element, "id").text = id_value


# Optional
def process_summary(entry_element, entry, feed_data):
    if "summary" in entry:
        # Convert summary type to Atom type
        type_mapping = {
            "text/plain": "text",
            "text/html": "html",
            "application/xhtml+xml": "xhtml",
        }
        summary_type = type_mapping.get(
            entry.get("summary_detail", {}).get("type"), "text"
        )
        ET.SubElement(
            entry_element, "summary", type=summary_type
        ).text = entry["summary"]


# Optional
def process_enclosures(entry_element, entry, feed_data):
    for enclosure in entry.get("enclosures", []):
        link_data = {
            "rel": "enclosure",
            "type": enclosure.get("type", "text/html"),
            "length": str(enclosure.get("length", "")),
            "href": enclosure["href"],
        }
        ET.SubElement(entry_element, "link", **link_data)


# Optional
def process_tags(entry_element, entry, feed_data):
    for tag in entry.get("tags", []):
        attrib_data = {
            "scheme": tag.get("scheme", ""),
            "label": tag.get("label", ""),
            "term": tag.get("term", ""),
        }
        ET.SubElement(entry_element, "category", **attrib_data)


# Required
def process_link(entry_element, entry, feed_data):
    # If link is not present, use feed id
    link_data = entry.get("link", feed_data["id"])
    link_attributes = {
        "rel": entry.get("rel", "alternate"),
        "type": entry.get("type", "text/html"),
        "href": link_data,
    }

    ET.SubElement(entry_element, "link", **link_attributes)


# Required
def process_author(entry_element, entry, feed_data):
    author = ET.SubElement(entry_element, "author")
    ET.SubElement(author, "name").text = entry.get("author", "Anonymous")


def output_feeds(slug, entries, feed_data, caching):
    """
    Output XML feeds to files.
    """

    output_file = f"rss-feeds/{slug}-feed.xml"
    xml = create_xml(entries, feed_data)

    if not os.path.exists("rss-feeds"):
        os.makedirs("rss-feeds")

    if not caching:
        with open(output_file, "w") as f:
            f.write(xml)
        return

    # If caching is enabled, append new entries to top of file
    if os.path.exists(output_file):
        with open(output_file, "r") as f:
            with open("newfile.txt", "w") as f2:
                f2.write(xml)
                f2.write(f.read())
        os.remove(output_file)
    else:
        with open("newfile.txt", "w") as f2:
            f2.write(xml)

    os.rename("newfile.txt", output_file)
