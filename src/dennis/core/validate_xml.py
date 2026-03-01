from lxml import etree
from xml.etree.ElementTree import tostring as std_tostring
from .export_xsd import generate_xsd


def validate_xml_file(xml_path: str) -> None:
    # Parse XML with lxml
    xml_doc = etree.parse(xml_path)

    # Generate stdlib XSD → bytes
    std_root = generate_xsd()
    xsd_bytes = std_tostring(std_root, encoding="utf-8")

    # Load into lxml
    xsd_doc = etree.XML(xsd_bytes)
    schema = etree.XMLSchema(xsd_doc)

    if not schema.validate(xml_doc):
        errors = "\n".join(str(e) for e in schema.error_log)
        raise ValueError(f"XML validation failed:\n{errors}")