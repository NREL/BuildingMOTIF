from rdflib import Graph, URIRef

from buildingmotif.dataclasses import Library


def test_get_template_body_plain_and_inline(client, building_motif):
    # Setup
    lib = Library.create("tmpl_body_lib")
    tmpl = lib.create_template("tmpl_body_test")
    # Add some triples to the template body
    tmpl.body.parse(
        data="""
@prefix : <urn:tmpl#> .
:s :p :o .
""",
        format="turtle",
    )
    building_motif.session.commit()

    # Act: plain body
    res_plain = client.get(f"/templates/{tmpl.id}/body")
    assert res_plain.status_code == 200
    g_plain = Graph().parse(data=res_plain.data, format="turtle")
    assert (URIRef("urn:tmpl#s"), URIRef("urn:tmpl#p"), URIRef("urn:tmpl#o")) in g_plain

    # Act: inlined body (should at least include original triples; with no deps, equal)
    res_inline = client.get(f"/templates/{tmpl.id}/body?inline=true")
    assert res_inline.status_code == 200
    g_inline = Graph().parse(data=res_inline.data, format="turtle")
    assert (URIRef("urn:tmpl#s"), URIRef("urn:tmpl#p"), URIRef("urn:tmpl#o")) in g_inline
