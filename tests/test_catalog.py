"""Catálogo público: acceso sin sesión, búsqueda y filtros combinados con datos reales."""
from conftest import make_product


def names(html):
    return html


def test_visitor_browses_everything_without_login(client, shop):
    for url in ("/", "/catalogo", f"/producto/{shop['shirt'].id}", "/catalogo?category=Camisas"):
        r = client.get(url)
        assert r.status_code == 200, url
    body = client.get("/catalogo").get_data(as_text=True)
    for p in shop.values():
        assert p.name in body  # todas las prendas, incluida la agotada


def test_home_is_a_storefront_not_a_login_form(client, shop):
    body = client.get("/").get_data(as_text=True)
    assert "Novedades" in body and "Compra por categoría" in body and 'name="q"' in body
    assert "Iniciar sesión" in body or "Ingresar" in body  # acceso visible, pero no obligatorio
    assert 'name="password"' not in body


def test_search_by_name(client, shop):
    body = client.get("/catalogo?q=oxford").get_data(as_text=True)
    assert "Camisa Oxford" in body and "Jean Slim" not in body


def test_search_escapes_like_wildcards(client, shop):
    body = client.get("/catalogo?q=%25").get_data(as_text=True)  # "%" no debe comportarse como comodín
    assert "0 prendas" in body


def test_filter_by_category_and_garment_type(client, shop):
    body = client.get("/catalogo?category=Camisas&garment_type=Camiseta").get_data(as_text=True)
    assert "Camiseta Blanca" in body and "Camisa Oxford" not in body


def test_filter_price_range(client, shop):
    body = client.get("/catalogo?min_price=50000&max_price=130000").get_data(as_text=True)
    assert "Camisa Oxford" in body and "Jean Slim" in body
    assert "Camiseta Blanca" not in body and "Vestido Midi" not in body


def test_filter_availability(client, shop):
    avail = client.get("/catalogo?availability=available").get_data(as_text=True)
    assert "Gorra Agotada" not in avail and "Camisa Oxford" in avail
    sold = client.get("/catalogo?availability=sold_out").get_data(as_text=True)
    assert "Gorra Agotada" in sold and "Camisa Oxford" not in sold


def test_filter_size_only_in_stock(client, shop):
    body = client.get("/catalogo?size=S").get_data(as_text=True)
    assert "Vestido Midi" in body and "Jean Slim" not in body
    # la talla 32 del jean existe pero está agotada: no debe listarlo
    assert "Jean Slim" not in client.get("/catalogo?size=32").get_data(as_text=True)
    assert "Jean Slim" in client.get("/catalogo?size=30").get_data(as_text=True)


def test_all_filters_work_together(client, shop):
    url = "/catalogo?q=jean&category=Pantalones&min_price=100000&max_price=150000&availability=available&size=30"
    assert "Jean Slim" in client.get(url).get_data(as_text=True)
    assert "Jean Slim" not in client.get(url.replace("size=30", "size=32")).get_data(as_text=True)
    assert "Jean Slim" not in client.get(url.replace("max_price=150000", "max_price=100000")).get_data(as_text=True)


def test_sorting(client, shop):
    asc = client.get("/catalogo?sort=price_asc").get_data(as_text=True)
    assert asc.index("Gorra Agotada") < asc.index("Camiseta Blanca") < asc.index("Vestido Midi")
    desc = client.get("/catalogo?sort=price_desc").get_data(as_text=True)
    assert desc.index("Vestido Midi") < desc.index("Camiseta Blanca")


def test_pagination_keeps_filters(client, app):
    for i in range(15):
        make_product(f"Prenda {i:02d}", 10000 + i, 5, "Camisas")
    page1 = client.get("/catalogo?category=Camisas").get_data(as_text=True)
    assert "15 prendas" in page1 and "page=2" in page1 and "category=Camisas" in page1
    page2 = client.get("/catalogo?category=Camisas&page=2").get_data(as_text=True)
    assert page2.count('class="product-card') == 3
    assert client.get("/catalogo?page=999").status_code == 200   # página fuera de rango: no falla


def test_garbage_parameters_do_not_break_page(client, shop):
    r = client.get("/catalogo?min_price=abc&max_price=-5&availability=zzz&sort=hack&page=x&size=%27")
    assert r.status_code == 200


def test_product_detail_shows_real_data_and_sizes(client, shop):
    body = client.get(f"/producto/{shop['dress'].id}").get_data(as_text=True)
    assert "Vestido Midi" in body and "$159.900" in body and "Vestido de prueba" in body or "Vestido Midi de prueba" in body
    for label in ("S", "M", "L"):
        assert f">{label}<" in body or f">{label}</label>" in body
    assert "Agregar al carrito" in body


def test_product_without_sizes_has_no_size_selector(client, shop):
    body = client.get(f"/producto/{shop['shirt'].id}").get_data(as_text=True)
    assert 'name="size_id"' not in body


def test_sold_out_product_cannot_be_added(client, shop):
    body = client.get(f"/producto/{shop['sold'].id}").get_data(as_text=True)
    assert "Agotado" in body and "disabled" in body


def test_missing_product_is_404(client, shop):
    assert client.get("/producto/9999").status_code == 404
