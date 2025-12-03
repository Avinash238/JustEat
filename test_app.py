import pytest
from app import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# --- Simple page tests ---
def test_home_page(client):
    rv = client.get('/')
    assert rv.status_code == 200
    assert b'Home' in rv.data

def test_login_page(client):
    rv = client.get('/login')
    assert rv.status_code == 200
    assert b'Login' in rv.data

def test_signup_page(client):
    rv = client.get('/signup')
    assert rv.status_code == 200
    assert b'Signup' in rv.data

# --- Customer cart ---
def test_customer_cart_redirect(client):
    rv = client.get('/customer/cart', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Please login first' in rv.data

def test_add_to_cart_redirect(client):
    rv = client.post('/add_to_cart/1', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Please login first' in rv.data

# --- Logout always works ---
def test_logout(client):
    rv = client.get('/logout', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Logged out successfully' in rv.data

# --- Owner tracking orders ---
def test_owner_track_orders_redirect(client):
    rv = client.get('/owner/track_orders', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Please login first' in rv.data

# --- Customer orders history ---
def test_customer_orders_history_redirect(client):
    rv = client.get('/customer/orders_history', follow_redirects=True)
    assert rv.status_code == 200
    assert b'Please login first' in rv.data

def test_customer_dashboard_page(client):
    rv = client.get('/customer/dashboard')
    assert rv.status_code == 200
    assert b'Restaurants' in rv.data or b'Deal' in rv.data  # should always render
