// book-ticket.js

// Listen for changes in ticket quantity and ticket type
document.getElementById('tickets').addEventListener('input', calculateTotal);
document.getElementById('ticket-type').addEventListener('change', calculateTotal);

// Function to calculate the total price based on selected ticket type and number of tickets
function calculateTotal() {
    const ticketType = document.getElementById('ticket-type').value;
    const numberOfTickets = document.getElementById('tickets').value;

    let pricePerTicket = 0;

    // Calculate the price per ticket based on the selected ticket type
    switch (ticketType) {
        case 'kids':
            pricePerTicket = 499; // ₹499 for Kids
            break;
        case 'single':
            pricePerTicket = 899; // ₹899 for Single
            break;
        case 'couple':
            pricePerTicket = 1599; // ₹1599 for Couple
            break;
        case 'couple+kid':
            pricePerTicket = 1999; // ₹1999 for Couple + Kid
            break;
        case 'defence':
            pricePerTicket = 899 * 0.5; // 50% discount on Single ticket (₹899)
            break;
    }

    // Calculate the total price
    const totalPrice = pricePerTicket * numberOfTickets;
    
    // Display the calculated total price
    document.getElementById('calculated-price').textContent = `₹${Math.round(totalPrice)}`;

    // Update the hidden field with the total price
    document.getElementById('hidden-total-price').value = Math.round(totalPrice);
    document.getElementById('hidden-ticket-type').value = ticketType;
}

// Function to update hidden fields when the form is submitted
function updateHiddenFields() {
    const ticketType = document.getElementById('ticket-type').value;
    const totalPrice = document.getElementById('calculated-price').textContent.replace('₹', '').trim();

    document.getElementById('hidden-ticket-type').value = ticketType;
    document.getElementById('hidden-total-price').value = totalPrice;
}

// Call updateHiddenFields before submitting the form
document.querySelector("form").addEventListener("submit", updateHiddenFields);
