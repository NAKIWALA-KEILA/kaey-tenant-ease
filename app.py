from flask import Flask, render_template, request, redirect, url_for, send_file
import sqlite3
from datetime import datetime
from num2words import num2words
from weasyprint import HTML
import io
import os

app = Flask(__name__)
DB_NAME = 'tenants.db'

# === Setup Database ===
def setup_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tenants (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            house_number TEXT,
            contact TEXT,
            nok1_name TEXT,
            nok1_contact TEXT,
            nok2_name TEXT,
            nok2_contact TEXT,
            monthly_rent INTEGER,
            last_payment_date TEXT,
            payment_status TEXT DEFAULT 'unpaid'
        )
    ''')
    conn.commit()
    conn.close()

# === Routes ===
@app.route('/')
def index():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM tenants")
    tenants = c.fetchall()
    conn.close()
    return render_template('index.html', tenants=tenants)

@app.route('/add', methods=['GET', 'POST'])
def add_tenant():
    if request.method == 'POST':
        name = request.form['name']
        house_number = request.form['house_number']
        contact = request.form['contact']
        nok1_name = request.form['nok1_name']
        nok1_contact = request.form['nok1_contact']
        nok2_name = request.form['nok2_name']
        nok2_contact = request.form['nok2_contact']
        monthly_rent = int(request.form['monthly_rent'])

        today = datetime.now().date().isoformat()

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('''
            INSERT INTO tenants VALUES (NULL,?,?,?,?,?,?,?,?,?,?)
        ''', (name, house_number, contact, nok1_name, nok1_contact, nok2_name, nok2_contact, monthly_rent, today, 'unpaid'))
        conn.commit()
        conn.close()
        return redirect(url_for('index'))

    return render_template('add_tenant.html')

@app.route('/mark_paid/<int:tenant_id>')
def mark_paid(tenant_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('UPDATE tenants SET payment_status = "paid", last_payment_date = ? WHERE id = ?', 
              (datetime.now().date().isoformat(), tenant_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/invoice/<int:tenant_id>', methods=['GET', 'POST'])
def generate_invoice(tenant_id):
    if request.method == 'POST':
        uedcl_prev = int(request.form['uedcl_prev'])
        uedcl_curr = int(request.form['uedcl_curr'])
        nswc_prev = int(request.form['nswc_prev'])
        nswc_curr = int(request.form['nswc_curr'])

        conn = sqlite3.connect(DB_NAME)
        c = conn.cursor()
        c.execute('SELECT * FROM tenants WHERE id=?', (tenant_id,))
        data = c.fetchone()
        conn.close()

        if not data:
            return "Tenant not found"

        name, house_number, contact, _, _, _, _, rent, _, _ = data

        uedcl_units = max(0, uedcl_curr - uedcl_prev)
        nswc_units = max(0, nswc_curr - nswc_prev)

        uedcl_cost = uedcl_units * 1200
        nswc_cost = nswc_units * 7000
        security_fee = 20000
        garbage_fee = 5000
        total = rent + uedcl_cost + nswc_cost + security_fee + garbage_fee
        amount_in_words = num2words(total, lang='en').title() + " Shillings Only"

        invoice_data = {
            'name': name,
            'house_number': house_number,
            'contact': contact,
            'rent': rent,
            'uedcl_units': uedcl_units,
            'uedcl_cost': uedcl_cost,
            'nswc_units': nswc_units,
            'nswc_cost': nswc_cost,
            'security_fee': security_fee,
            'garbage_fee': garbage_fee,
            'total': total,
            'amount_in_words': amount_in_words
        }

        return render_template('invoice_preview.html', invoice=invoice_data, tenant_id=tenant_id)

    return render_template('generate_invoice.html', tenant_id=tenant_id)

@app.route('/download_invoice/<int:tenant_id>')
def download_invoice(tenant_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('SELECT * FROM tenants WHERE id=?', (tenant_id,))
    data = c.fetchone()
    conn.close()

    if not data:
        return "Tenant not found"

    name, house_number, contact, _, _, _, _, rent, _, _ = data

    uedcl_prev = request.args.get('uedcl_prev', default=0, type=int)
    uedcl_curr = request.args.get('uedcl_curr', default=0, type=int)
    nswc_prev = request.args.get('nswc_prev', default=0, type=int)
    nswc_curr = request.args.get('nswc_curr', default=0, type=int)

    uedcl_units = max(0, uedcl_curr - uedcl_prev)
    nswc_units = max(0, nswc_curr - nswc_prev)

    uedcl_cost = uedcl_units * 1200
    nswc_cost = nswc_units * 7000
    security_fee = 20000
    garbage_fee = 5000
    total = rent + uedcl_cost + nswc_cost + security_fee + garbage_fee
    amount_in_words = num2words(total, lang='en').title() + " Shillings Only"

    invoice_data = {
        'name': name,
        'house_number': house_number,
        'contact': contact,
        'rent': rent,
        'uedcl_units': uedcl_units,
        'uedcl_cost': uedcl_cost,
        'nswc_units': nswc_units,
        'nswc_cost': nswc_cost,
        'security_fee': security_fee,
        'garbage_fee': garbage_fee,
        'total': total,
        'amount_in_words': amount_in_words
    }

    rendered = render_template('invoice_pdf.html', invoice=invoice_data)

    # Generate PDF
    pdf = HTML(string=rendered).write_pdf()

    # Send PDF as download
    return send_file(
        io.BytesIO(pdf),
        download_name=f"Invoice_{name}_{house_number}.pdf",
        as_attachment=True,
        mimetype='application/pdf'
    )

if __name__ == '__main__':
    setup_db()
    app.run(debug=True)
