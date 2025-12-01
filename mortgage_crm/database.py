"""
Database module for Mortgage CRM
SQLite database for storing clients, users, and loan data

Schema based on Phase 2 specifications:
- Users (loan officers and admins)
- Clients (borrowers with all mortgage and calculation fields)
- Admin Settings (global defaults)
"""

import sqlite3
import os
from datetime import datetime
import json

DATABASE_FILE = "mortgage_crm.db"


def get_connection():
    """Get database connection"""
    conn = sqlite3.connect(DATABASE_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def init_database():
    """Initialize database tables per Phase 2 schema"""
    conn = get_connection()
    cursor = conn.cursor()

    # Users table (loan officers and admins)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'loan_officer',
            full_name TEXT,
            email TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Clients table (unified schema with all fields)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            loan_officer_id INTEGER,

            -- Basic Info
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,

            -- Current Mortgage Info (for Calculator #1 - ADL model)
            current_mortgage_balance REAL,
            current_mortgage_rate REAL,
            remaining_years INTEGER,

            -- Rate Calculation Inputs (for Calculator #2 - LLPA)
            credit_score INTEGER,
            property_value REAL,
            loan_amount REAL,
            ltv REAL,
            property_type TEXT DEFAULT 'Single Family',
            occupancy TEXT DEFAULT 'Primary Residence',
            loan_purpose TEXT DEFAULT 'Rate/Term Refinance',
            state TEXT,
            loan_type TEXT DEFAULT 'Conventional',

            -- Economic Parameters (Calculator #1) - can use defaults
            discount_rate REAL DEFAULT 0.05,
            rate_volatility REAL DEFAULT 0.0109,
            tax_rate REAL DEFAULT 0.28,
            fixed_refi_cost REAL DEFAULT 2000,
            points_pct REAL DEFAULT 0.01,
            prob_moving REAL DEFAULT 0.10,
            inflation_rate REAL DEFAULT 0.03,

            -- Calculated Fields (updated on save)
            optimal_rate_drop REAL,
            trigger_rate REAL,
            available_rate REAL,
            difference REAL,
            ready_to_refinance BOOLEAN DEFAULT FALSE,

            -- Timestamps
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_rate_check TIMESTAMP,

            FOREIGN KEY (loan_officer_id) REFERENCES users(id)
        )
    """)

    # Admin Settings (global defaults)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY,
            value TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Rate checks history (track when we checked rates for clients)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_checks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            check_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            available_rate REAL NOT NULL,
            trigger_rate REAL NOT NULL,
            difference REAL NOT NULL,
            is_ready_to_refinance BOOLEAN,
            details TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id)
        )
    """)

    # Contact log
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contact_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            contact_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            contact_type TEXT,
            notes TEXT,
            outcome TEXT,
            FOREIGN KEY (client_id) REFERENCES clients (id),
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)

    # Initialize default admin settings
    default_settings = {
        'default_discount_rate': '0.05',
        'default_volatility': '0.0109',
        'default_tax_rate': '0.28',
        'default_fixed_cost': '2000',
        'default_points': '0.01',
        'default_prob_moving': '0.10',
        'default_inflation': '0.03',
        'base_rate_conventional': '6.500',
        'base_rate_fha': '6.250'
    }

    for key, value in default_settings.items():
        cursor.execute("""
            INSERT OR IGNORE INTO admin_settings (key, value) VALUES (?, ?)
        """, (key, value))

    conn.commit()
    conn.close()


# =============================================================================
# USER FUNCTIONS
# =============================================================================

def create_user(username: str, password_hash: str, role: str = 'loan_officer',
                full_name: str = None, email: str = None):
    """Create a new user"""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, email)
            VALUES (?, ?, ?, ?, ?)
        """, (username, password_hash, role, full_name, email))
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def get_user_by_username(username: str):
    """Get user by username"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_user_by_id(user_id: int):
    """Get user by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None


def get_all_users():
    """Get all users"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, role, full_name, email, created_at FROM users")
    users = cursor.fetchall()
    conn.close()
    return [dict(u) for u in users]


def delete_user(user_id: int):
    """Delete a user"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def update_user_password(user_id: int, password_hash: str):
    """Update user password"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET password_hash = ? WHERE id = ?", (password_hash, user_id))
    conn.commit()
    conn.close()


# =============================================================================
# CLIENT FUNCTIONS (New unified schema)
# =============================================================================

def create_client(loan_officer_id: int, client_data: dict) -> int:
    """Create a new client with all fields"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO clients (
            loan_officer_id, first_name, last_name, email, phone,
            current_mortgage_balance, current_mortgage_rate, remaining_years,
            credit_score, property_value, loan_amount, ltv,
            property_type, occupancy, loan_purpose, state, loan_type,
            discount_rate, rate_volatility, tax_rate, fixed_refi_cost,
            points_pct, prob_moving, inflation_rate,
            optimal_rate_drop, trigger_rate, available_rate, difference, ready_to_refinance
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        loan_officer_id,
        client_data.get('first_name'),
        client_data.get('last_name'),
        client_data.get('email'),
        client_data.get('phone'),
        client_data.get('current_mortgage_balance'),
        client_data.get('current_mortgage_rate'),
        client_data.get('remaining_years'),
        client_data.get('credit_score'),
        client_data.get('property_value'),
        client_data.get('loan_amount'),
        client_data.get('ltv'),
        client_data.get('property_type', 'Single Family'),
        client_data.get('occupancy', 'Primary Residence'),
        client_data.get('loan_purpose', 'Rate/Term Refinance'),
        client_data.get('state'),
        client_data.get('loan_type', 'Conventional'),
        client_data.get('discount_rate', 0.05),
        client_data.get('rate_volatility', 0.0109),
        client_data.get('tax_rate', 0.28),
        client_data.get('fixed_refi_cost', 2000),
        client_data.get('points_pct', 0.01),
        client_data.get('prob_moving', 0.10),
        client_data.get('inflation_rate', 0.03),
        client_data.get('optimal_rate_drop'),
        client_data.get('trigger_rate'),
        client_data.get('available_rate'),
        client_data.get('difference'),
        client_data.get('ready_to_refinance', False)
    ))

    conn.commit()
    client_id = cursor.lastrowid
    conn.close()
    return client_id


def get_clients_by_user(user_id: int, ready_only: bool = False, search: str = None):
    """Get all clients for a loan officer"""
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM clients WHERE loan_officer_id = ?"
    params = [user_id]

    if ready_only:
        query += " AND ready_to_refinance = 1"

    if search:
        query += " AND (first_name LIKE ? OR last_name LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    query += " ORDER BY difference DESC, last_name, first_name"

    cursor.execute(query, params)
    clients = cursor.fetchall()
    conn.close()
    return [dict(c) for c in clients]


def get_all_clients():
    """Get all clients (admin function)"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.*, u.full_name as loan_officer_name, u.username as loan_officer_username
        FROM clients c
        LEFT JOIN users u ON c.loan_officer_id = u.id
        ORDER BY c.difference DESC
    """)
    clients = cursor.fetchall()
    conn.close()
    return [dict(c) for c in clients]


def get_client_by_id(client_id: int):
    """Get client by ID"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clients WHERE id = ?", (client_id,))
    client = cursor.fetchone()
    conn.close()
    return dict(client) if client else None


def update_client(client_id: int, client_data: dict):
    """Update client with all fields"""
    conn = get_connection()
    cursor = conn.cursor()

    # Build dynamic update
    allowed_fields = [
        'first_name', 'last_name', 'email', 'phone',
        'current_mortgage_balance', 'current_mortgage_rate', 'remaining_years',
        'credit_score', 'property_value', 'loan_amount', 'ltv',
        'property_type', 'occupancy', 'loan_purpose', 'state', 'loan_type',
        'discount_rate', 'rate_volatility', 'tax_rate', 'fixed_refi_cost',
        'points_pct', 'prob_moving', 'inflation_rate',
        'optimal_rate_drop', 'trigger_rate', 'available_rate', 'difference',
        'ready_to_refinance', 'last_rate_check'
    ]

    fields = []
    values = []
    for key, value in client_data.items():
        if key in allowed_fields:
            fields.append(f"{key} = ?")
            values.append(value)

    if fields:
        fields.append("updated_at = ?")
        values.append(datetime.now())
        values.append(client_id)

        query = f"UPDATE clients SET {', '.join(fields)} WHERE id = ?"
        cursor.execute(query, values)
        conn.commit()

    conn.close()


def delete_client(client_id: int):
    """Delete a client and related data"""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM rate_checks WHERE client_id = ?", (client_id,))
    cursor.execute("DELETE FROM contact_log WHERE client_id = ?", (client_id,))
    cursor.execute("DELETE FROM clients WHERE id = ?", (client_id,))

    conn.commit()
    conn.close()


def bulk_update_client_rates(loan_officer_id: int = None):
    """Recalculate rates for all clients (or just one loan officer's clients)"""
    from utils.optimal_threshold import calculate_trigger_rate
    from utils.rate_calculator import calculate_available_rate

    conn = get_connection()
    cursor = conn.cursor()

    if loan_officer_id:
        cursor.execute("SELECT * FROM clients WHERE loan_officer_id = ?", (loan_officer_id,))
    else:
        cursor.execute("SELECT * FROM clients")

    clients = cursor.fetchall()
    conn.close()

    # Load config for base rates
    config = get_admin_settings()
    base_rate_conv = float(config.get('base_rate_conventional', 6.5))
    base_rate_fha = float(config.get('base_rate_fha', 6.25))

    updated_count = 0
    for client in clients:
        client = dict(client)
        if client.get('current_mortgage_rate') and client.get('current_mortgage_balance'):
            # Calculate trigger rate using ADL model
            result = calculate_trigger_rate(
                current_rate=client['current_mortgage_rate'],
                remaining_balance=client['current_mortgage_balance'],
                remaining_years=client.get('remaining_years', 25),
                discount_rate=client.get('discount_rate', 0.05),
                volatility=client.get('rate_volatility', 0.0109),
                tax_rate=client.get('tax_rate', 0.28),
                fixed_cost=client.get('fixed_refi_cost', 2000),
                points=client.get('points_pct', 0.01),
                prob_moving=client.get('prob_moving', 0.10),
                inflation_rate=client.get('inflation_rate', 0.03)
            )

            trigger_rate = result.get('trigger_rate')
            optimal_rate_drop = result.get('optimal_threshold_bps')

            # Calculate available rate
            base_rate = base_rate_fha if client.get('loan_type') == 'FHA' else base_rate_conv
            rate_info = calculate_available_rate(
                base_rate=base_rate,
                credit_score=client.get('credit_score', 720),
                ltv=client.get('ltv', 80),
                loan_amount=client.get('loan_amount') or client.get('current_mortgage_balance'),
                loan_type=client.get('loan_type', 'Conventional'),
                property_type=client.get('property_type', 'Single Family'),
                occupancy=client.get('occupancy', 'Primary Residence')
            )
            available_rate = rate_info['final_rate'] / 100  # Convert to decimal

            # Calculate difference
            difference = trigger_rate - available_rate if trigger_rate else None
            ready = difference > 0 if difference else False

            # Update client
            update_client(client['id'], {
                'optimal_rate_drop': optimal_rate_drop,
                'trigger_rate': trigger_rate,
                'available_rate': available_rate,
                'difference': difference,
                'ready_to_refinance': ready,
                'last_rate_check': datetime.now()
            })
            updated_count += 1

    return updated_count


# =============================================================================
# RATE CHECK FUNCTIONS
# =============================================================================

def log_rate_check(client_id: int, available_rate: float, trigger_rate: float,
                   difference: float, is_ready: bool, details: str = None):
    """Log a rate check for a client"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO rate_checks (client_id, available_rate, trigger_rate, difference,
                                 is_ready_to_refinance, details)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (client_id, available_rate, trigger_rate, difference, is_ready, details))
    conn.commit()
    conn.close()


def get_rate_check_history(client_id: int, limit: int = 10):
    """Get rate check history for a client"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM rate_checks WHERE client_id = ?
        ORDER BY check_date DESC LIMIT ?
    """, (client_id, limit))
    checks = cursor.fetchall()
    conn.close()
    return [dict(c) for c in checks]


# =============================================================================
# CONTACT LOG FUNCTIONS
# =============================================================================

def log_contact(client_id: int, user_id: int, contact_type: str, notes: str = None, outcome: str = None):
    """Log a contact with a client"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO contact_log (client_id, user_id, contact_type, notes, outcome)
        VALUES (?, ?, ?, ?, ?)
    """, (client_id, user_id, contact_type, notes, outcome))
    conn.commit()
    conn.close()


def get_contact_history(client_id: int, limit: int = 20):
    """Get contact history for a client"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT cl.*, u.full_name as contacted_by
        FROM contact_log cl
        JOIN users u ON cl.user_id = u.id
        WHERE cl.client_id = ?
        ORDER BY cl.contact_date DESC LIMIT ?
    """, (client_id, limit))
    contacts = cursor.fetchall()
    conn.close()
    return [dict(c) for c in contacts]


# =============================================================================
# ADMIN SETTINGS FUNCTIONS
# =============================================================================

def get_admin_settings() -> dict:
    """Get all admin settings as a dictionary"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT key, value FROM admin_settings")
    settings = cursor.fetchall()
    conn.close()
    return {s['key']: s['value'] for s in settings}


def get_admin_setting(key: str, default: str = None) -> str:
    """Get a single admin setting"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT value FROM admin_settings WHERE key = ?", (key,))
    result = cursor.fetchone()
    conn.close()
    return result['value'] if result else default


def set_admin_setting(key: str, value: str):
    """Set an admin setting"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR REPLACE INTO admin_settings (key, value, updated_at)
        VALUES (?, ?, ?)
    """, (key, value, datetime.now()))
    conn.commit()
    conn.close()


def apply_defaults_to_all_clients():
    """Apply current default settings to all existing clients"""
    settings = get_admin_settings()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE clients SET
            discount_rate = ?,
            rate_volatility = ?,
            tax_rate = ?,
            fixed_refi_cost = ?,
            points_pct = ?,
            prob_moving = ?,
            inflation_rate = ?,
            updated_at = ?
    """, (
        float(settings.get('default_discount_rate', 0.05)),
        float(settings.get('default_volatility', 0.0109)),
        float(settings.get('default_tax_rate', 0.28)),
        float(settings.get('default_fixed_cost', 2000)),
        float(settings.get('default_points', 0.01)),
        float(settings.get('default_prob_moving', 0.10)),
        float(settings.get('default_inflation', 0.03)),
        datetime.now()
    ))
    count = cursor.rowcount
    conn.commit()
    conn.close()
    return count


# =============================================================================
# SEED DATA FUNCTIONS
# =============================================================================

def seed_users(password_hash_func):
    """Seed initial users if none exist"""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM users")
    count = cursor.fetchone()['count']
    conn.close()

    if count == 0:
        SEED_USERS = [
            {"username": "admin", "password": "admin123", "role": "admin", "full_name": "Administrator"},
            {"username": "john_lo", "password": "loan123", "role": "loan_officer", "full_name": "John Smith"},
            {"username": "sarah_lo", "password": "loan456", "role": "loan_officer", "full_name": "Sarah Johnson"},
        ]

        for user in SEED_USERS:
            create_user(
                username=user['username'],
                password_hash=password_hash_func(user['password']),
                role=user['role'],
                full_name=user['full_name']
            )
        return len(SEED_USERS)
    return 0


def seed_clients(loan_officer_id: int):
    """Seed sample clients for a loan officer"""
    from utils.optimal_threshold import calculate_trigger_rate
    from utils.rate_calculator import calculate_available_rate

    settings = get_admin_settings()
    base_rate_conv = float(settings.get('base_rate_conventional', 6.5))
    base_rate_fha = float(settings.get('base_rate_fha', 6.25))

    SAMPLE_CLIENTS = [
        # Ready to refinance (difference > 0)
        {"first_name": "Michael", "last_name": "Johnson", "email": "michael.j@email.com", "phone": "555-0101",
         "current_mortgage_rate": 0.075, "current_mortgage_balance": 350000, "remaining_years": 25,
         "credit_score": 740, "property_value": 450000, "ltv": 77.8, "state": "California", "loan_type": "Conventional"},

        {"first_name": "Emily", "last_name": "Davis", "email": "emily.d@email.com", "phone": "555-0102",
         "current_mortgage_rate": 0.072, "current_mortgage_balance": 425000, "remaining_years": 28,
         "credit_score": 780, "property_value": 550000, "ltv": 77.3, "state": "Texas", "loan_type": "Conventional"},

        {"first_name": "Robert", "last_name": "Wilson", "email": "robert.w@email.com", "phone": "555-0103",
         "current_mortgage_rate": 0.078, "current_mortgage_balance": 280000, "remaining_years": 20,
         "credit_score": 760, "property_value": 380000, "ltv": 73.7, "state": "Florida", "loan_type": "Conventional"},

        {"first_name": "Jennifer", "last_name": "Martinez", "email": "jennifer.m@email.com", "phone": "555-0104",
         "current_mortgage_rate": 0.068, "current_mortgage_balance": 520000, "remaining_years": 27,
         "credit_score": 800, "property_value": 700000, "ltv": 74.3, "state": "New York", "loan_type": "Conventional"},

        # Not quite ready (waiting)
        {"first_name": "David", "last_name": "Brown", "email": "david.b@email.com", "phone": "555-0105",
         "current_mortgage_rate": 0.065, "current_mortgage_balance": 300000, "remaining_years": 22,
         "credit_score": 720, "property_value": 400000, "ltv": 75.0, "state": "Arizona", "loan_type": "Conventional"},

        {"first_name": "Lisa", "last_name": "Anderson", "email": "lisa.a@email.com", "phone": "555-0106",
         "current_mortgage_rate": 0.062, "current_mortgage_balance": 380000, "remaining_years": 26,
         "credit_score": 700, "property_value": 480000, "ltv": 79.2, "state": "Colorado", "loan_type": "FHA"},

        {"first_name": "James", "last_name": "Taylor", "email": "james.t@email.com", "phone": "555-0107",
         "current_mortgage_rate": 0.064, "current_mortgage_balance": 450000, "remaining_years": 24,
         "credit_score": 680, "property_value": 560000, "ltv": 80.4, "state": "Washington", "loan_type": "FHA"},

        {"first_name": "Amanda", "last_name": "Thomas", "email": "amanda.t@email.com", "phone": "555-0108",
         "current_mortgage_rate": 0.070, "current_mortgage_balance": 275000, "remaining_years": 18,
         "credit_score": 750, "property_value": 350000, "ltv": 78.6, "state": "Oregon", "loan_type": "Conventional"},

        {"first_name": "Christopher", "last_name": "Garcia", "email": "chris.g@email.com", "phone": "555-0109",
         "current_mortgage_rate": 0.073, "current_mortgage_balance": 600000, "remaining_years": 29,
         "credit_score": 770, "property_value": 800000, "ltv": 75.0, "state": "California", "loan_type": "Conventional"},

        {"first_name": "Michelle", "last_name": "Rodriguez", "email": "michelle.r@email.com", "phone": "555-0110",
         "current_mortgage_rate": 0.066, "current_mortgage_balance": 320000, "remaining_years": 23,
         "credit_score": 710, "property_value": 420000, "ltv": 76.2, "state": "Nevada", "loan_type": "Conventional"},
    ]

    created_count = 0
    for client_data in SAMPLE_CLIENTS:
        # Set defaults
        client_data['loan_amount'] = client_data['current_mortgage_balance']
        client_data['property_type'] = 'Single Family'
        client_data['occupancy'] = 'Primary Residence'
        client_data['loan_purpose'] = 'Rate/Term Refinance'

        # Calculate trigger rate
        result = calculate_trigger_rate(
            current_rate=client_data['current_mortgage_rate'],
            remaining_balance=client_data['current_mortgage_balance'],
            remaining_years=client_data['remaining_years']
        )

        client_data['trigger_rate'] = result.get('trigger_rate')
        client_data['optimal_rate_drop'] = result.get('optimal_threshold_bps')

        # Calculate available rate
        base_rate = base_rate_fha if client_data['loan_type'] == 'FHA' else base_rate_conv
        rate_info = calculate_available_rate(
            base_rate=base_rate,
            credit_score=client_data['credit_score'],
            ltv=client_data['ltv'],
            loan_amount=client_data['loan_amount'],
            loan_type=client_data['loan_type']
        )
        client_data['available_rate'] = rate_info['final_rate'] / 100

        # Calculate difference
        if client_data['trigger_rate']:
            client_data['difference'] = client_data['trigger_rate'] - client_data['available_rate']
            client_data['ready_to_refinance'] = client_data['difference'] > 0
        else:
            client_data['difference'] = None
            client_data['ready_to_refinance'] = False

        create_client(loan_officer_id, client_data)
        created_count += 1

    return created_count


# Initialize database on import
init_database()
