from flask import Flask, render_template, request, redirect, url_for, jsonify, session
import qrcode
import io
import base64
import uuid
import random
from datetime import datetime, timedelta
from flask_mysqldb import MySQL
import os

app = Flask(__name__, template_folder='../templates', static_folder='../static')
app.secret_key = 'your_secret_key_here'  # Change this!

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'adminstar'
app.config['MYSQL_PASSWORD'] = '987654321'
app.config['MYSQL_DB'] = 'waterpark'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'

mysql = MySQL(app)

@app.route('/')
def home():
    return render_template('index.html')

reviews=[]
@app.route('/photos')
def photos():
    return render_template('photos.html')

@app.route('/reviews')
def show_reviews():
    return render_template('reviews.html', reviews=reviews)

# Corrected and organized contact routes
@app.route('/contact-us')  
def main_contact_page():  
    return render_template('contact.html')

@app.route('/contact-form', endpoint='contact_form')
def contact_form_page():
    return render_template('contact.html')  # Same template if needed

@app.route('/whatsapp-contact')
def whatsapp_contact_page():
    return render_template('whatsapp_enquiry.html')

@app.route('/submit-review', methods=['POST'])
def submit_review():
    name = request.form.get('name', 'Anonymous').strip()
    email = request.form.get('email', '').strip()
    content = request.form.get('review', '').strip()
    
    # Basic validation
    if not content:
        return "Review content is required", 400
    
    date = datetime.now().strftime("%B %d, %Y %H:%M")
    
    reviews.append({
        'name': name,
        'email': email,
        'content': content,
        'date': date
    })
    
    return redirect(url_for('show_reviews'))


@app.route('/book-ticket', methods=['GET', 'POST'])
def book_ticket():
    if request.method == 'POST':
        name = request.form.get('name')
        mobile = request.form.get('mobile')
        email = request.form.get('email')
        date = request.form.get('date')
        ticket_type = request.form.get('ticket-type')
        tickets = request.form.get('tickets')
        is_defence = request.form.get('is_defence', 'off') == 'on'
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO tickets (name, email, date, tickets, mobile) VALUES (%s, %s, %s, %s, %s)", (name, email, date, tickets, mobile))
        mysql.connection.commit()
        cur.close()
        
        # Store in session for payment page
        session['booking_data'] = {
            'ticket_type': ticket_type,
            'ticket_count': tickets,
            'mobile': mobile,
            'is_defence': is_defence
        }
        return redirect(url_for('payment'))
    
    return render_template('book_ticket.html')

@app.route('/payment')
def payment():
    booking_data = session.get('booking_data', {})
    
    if not booking_data:
        return redirect(url_for('book_ticket'))
    
    # Price calculation
    prices = {
        'kids': 499,
        'single': 899,
        'couple': 1599,
        'couple+kid': 1999,
        'defence': 899 * 0.5
    }
    
    ticket_type = booking_data.get('ticket_type', 'single')
    ticket_count = int(booking_data.get('ticket_count', 1))
    is_defence = booking_data.get('is_defence', False)
    
    price_per_ticket = prices.get(ticket_type, 899)
    if is_defence and ticket_type != 'defence':
        price_per_ticket *= 0.5
        
    total_price = price_per_ticket * ticket_count
    
    return render_template('payment.html',
                         ticket_type=ticket_type,
                         ticket_count=ticket_count,
                         total_price=total_price,
                         mobile=booking_data.get('mobile'))

@app.route('/generate-qr', methods=['POST'])
def generate_qr():
    try:
        total_price = float(request.form.get('total_price', 0))
        mobile = request.form.get('mobile', '')
        ticket_type = request.form.get('ticket_type', '')
        ticket_count = int(request.form.get('ticket_count', 1))
        
        # Generate transaction details with expiration
        transaction_id = f"WP{datetime.now().strftime('%Y%m%d%H%M%S')}{random.randint(1000, 9999)}"
        expires_at = datetime.now() + timedelta(minutes=10)
        
        # Merchant UPI details (replace with your actual UPI ID)
        merchant_vpa = "8607564817@ybl"
        merchant_name = "Waterpark Tickets"
        
        # Create UPI payment URI
        upi_uri = f"upi://pay?pa={merchant_vpa}&pn={merchant_name}&am={total_price:.2f}&tn=WaterparkTicket{transaction_id}"
        
        # Generate QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(upi_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Save to database
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO payments 
            (transaction_id, amount, mobile, ticket_type, ticket_count, status, expires_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (transaction_id, total_price, mobile, ticket_type, ticket_count, 'COMPLETED', expires_at))
        mysql.connection.commit()
        cur.close()

        print(jsonify({
            'success': True,
            'qr_code': base64.b64encode(buffer.getvalue()).decode(),
            'transaction_id': transaction_id,
            'amount': total_price,
            'upi_uri': upi_uri,
            'expires_at': expires_at.isoformat()
        }))
        
        return jsonify({
            'success': True,
            'qr_code': base64.b64encode(buffer.getvalue()).decode(),
            'transaction_id': transaction_id,
            'amount': total_price,
            'upi_uri': upi_uri,
            'expires_at': expires_at.isoformat()
        })
        
        
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    

@app.route('/check-payment/<transaction_id>', methods=['GET'])
def check_payment(transaction_id):
    try:

        print(f"Received check payment request for transaction: {transaction_id}")  # Debug log
        
        if not transaction_id or len(transaction_id) < 5:  # Basic validation
            return jsonify({'success': False, 'message': 'Invalid transaction ID'}), 400
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT status FROM payments 
            WHERE transaction_id = %s
        """, (transaction_id,))
        result = cur.fetchone()
        cur.close()
        
        if not result:
            return jsonify({'success': False, 'message': 'Transaction not found'}), 404
            
        status = result[0]
        print(status)
        print(jsonify({
                'success': True,
                'status': 'SUCCESS',
                'message': 'Payment Successful! Your tickets have been booked.'
            }),"88888888888888888888888888888888888888888888888888")
        
        if status == 'SUCCESS':
            return jsonify({
                'success': True,
                'status': 'SUCCESS',
                'message': 'Payment Successful! Your tickets have been booked.'
            })
        else:
            return jsonify({
                'success': True,
                'status': status,
                'message': 'Payment is still pending. Please complete the payment.'
            })
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 400

# Add these endpoints to your Flask app

@app.route('/verify-payment/<transaction_id>', methods=['GET'])
def verify_payment(transaction_id):
    try:
        cur = mysql.connection.cursor()
        
        # Check if payment exists and get status
        cur.execute("""
            SELECT status, amount, mobile, ticket_type, ticket_count 
            FROM payments 
            WHERE transaction_id = %s
        """, (transaction_id,))
        
        result = cur.fetchone()
        print(result)
        cur.close()
        
        if not result:
            print(jsonify({
                'success': False,
                'message': 'Transaction not found',
                'paid': False
            }), 404)
            return jsonify({
                'success': False,
                'message': 'Transaction not found',
                'paid': False
            }), 404
        
        status, amount, mobile, ticket_type, ticket_count = result
        print(jsonify({
            'success': True,
            'status': status,
            'paid': status == 'SUCCESS',
            'amount': float(amount),
            'mobile': mobile,
            'ticket_type': ticket_type,
            'ticket_count': ticket_count,
            'message': 'Payment verified' if status == 'SUCCESS' else f'Payment status: {status}'
        }))
        return jsonify({
            'success': True,
            'status': status,
            'paid': status == 'SUCCESS',
            'amount': float(amount),
            'mobile': mobile,
            'ticket_type': ticket_type,
            'ticket_count': ticket_count,
            'message': 'Payment verified' if status == 'SUCCESS' else f'Payment status: {status}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e),
            'paid': False
        }), 500

@app.route('/update-payment-status', methods=['POST'])
def update_payment_status():
    try:
        data = request.get_json()
        transaction_id = data.get('transaction_id')
        status = data.get('status')
        
        if not transaction_id or not status:
            return jsonify({
                'success': False,
                'message': 'Missing transaction_id or status'
            }), 400
        
        valid_statuses = ['PENDING', 'SUCCESS', 'FAILED', 'EXPIRED']
        if status not in valid_statuses:
            return jsonify({
                'success': False,
                'message': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'
            }), 400
        
        cur = mysql.connection.cursor()
        
        # Check if transaction exists first
        cur.execute("SELECT 1 FROM payments WHERE transaction_id = %s", (transaction_id,))
        if not cur.fetchone():
            cur.close()
            return jsonify({
                'success': False,
                'message': 'Transaction not found'
            }), 404
        
        # Update status
        cur.execute("""
            UPDATE payments 
            SET status = %s, updated_at = NOW() 
            WHERE transaction_id = %s
        """, (status, transaction_id))
        
        mysql.connection.commit()
        cur.close()
        
        return jsonify({
            'success': True,
            'message': 'Payment status updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@app.route('/payment-success')
def payment_success():
    return render_template('payment_success.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8080))  # Use Render's assigned port
    app.run(debug=True, port=8080)
