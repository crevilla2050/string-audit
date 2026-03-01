from xml.etree.ElementTree import Element, SubElement, ElementTree

XS = "http://www.w3.org/2001/XMLSchema"


def generate_xsd():
    schema = Element(f"{{{XS}}}schema", attrib={"elementFormDefault": "qualified"})

    # Root element
    plan = SubElement(schema, f"{{{XS}}}element", name="plan")
    plan_type = SubElement(plan, f"{{{XS}}}complexType")

    # Sequence FIRST
    plan_seq = SubElement(plan_type, f"{{{XS}}}sequence")

    # meta element
    meta = SubElement(plan_seq, f"{{{XS}}}element", name="meta", minOccurs="0")
    meta_type = SubElement(meta, f"{{{XS}}}complexType")
    SubElement(meta_type, f"{{{XS}}}attribute", name="generated_at", type="xs:string")

    # changes container
    changes = SubElement(plan_seq, f"{{{XS}}}element", name="changes")
    changes_type = SubElement(changes, f"{{{XS}}}complexType")
    changes_seq = SubElement(changes_type, f"{{{XS}}}sequence")

    # change entries
    change = SubElement(changes_seq, f"{{{XS}}}element", name="change", maxOccurs="unbounded")
    change_type = SubElement(change, f"{{{XS}}}complexType")

    # inner elements FIRST
    change_seq = SubElement(change_type, f"{{{XS}}}sequence")
    for name in ("file", "line", "original", "replacement"):
        SubElement(change_seq, f"{{{XS}}}element", name=name, type="xs:string")

    # THEN attributes
    SubElement(change_type, f"{{{XS}}}attribute", name="id", type="xs:string")
    SubElement(change_type, f"{{{XS}}}attribute", name="token", type="xs:string")

    # plan attributes LAST
    SubElement(plan_type, f"{{{XS}}}attribute", name="version", type="xs:string")

    return schema


def export_xsd(fp):
    ElementTree(generate_xsd()).write(fp, encoding="utf-8", xml_declaration=True)