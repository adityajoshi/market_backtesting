document.addEventListener('DOMContentLoaded', function() {

    // Helper to format date with slashes (mm/dd/yyyy)
    function formatDateInput(e) {
        let val = e.target.value.replace(/\D/g, ''); // Remove non-digits
        if (val.length > 8) {
            val = val.substring(0, 8); // Max 8 digits
        }

        let formatted = val;
        if (val.length > 2) {
            formatted = val.substring(0, 2) + '/' + val.substring(2);
        }
        if (val.length > 4) {
            formatted = formatted.substring(0, 5) + '/' + formatted.substring(5, 9);
        }
        e.target.value = formatted;
    }

    const buyDateInput = document.getElementById('buy_date');
    const sellDateInput = document.getElementById('sell_date');

    buyDateInput.addEventListener('input', formatDateInput);
    sellDateInput.addEventListener('input', formatDateInput);

    // Helper to round price to 0 decimals
    function roundPriceInput(e) {
        let val = parseFloat(e.target.value);
        if (!isNaN(val)) {
            e.target.value = Math.round(val);
        }
    }

    const buyPriceInput = document.getElementById('buy_price');
    const sellPriceInput = document.getElementById('sell_price');

    buyPriceInput.addEventListener('blur', roundPriceInput);
    sellPriceInput.addEventListener('blur', roundPriceInput);

    // Handle form submission
    const form = document.getElementById('tradeForm');
    const messageDiv = document.getElementById('message');

    form.addEventListener('submit', async function(e) {
        e.preventDefault();
        messageDiv.textContent = '';
        messageDiv.className = '';

        const formData = {
            stock_name: document.getElementById('stock_name').value,
            buy_date: document.getElementById('buy_date').value,
            sell_date: document.getElementById('sell_date').value,
            buy_price: document.getElementById('buy_price').value,
            sell_price: document.getElementById('sell_price').value,
            strategy_name: document.getElementById('strategy_name').value,
        };

        try {
            const response = await fetch('/save', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(formData)
            });

            const result = await response.json();

            if (response.ok) {
                messageDiv.textContent = result.message;
                messageDiv.classList.add('success');
                form.reset();
            } else {
                messageDiv.textContent = 'Error: ' + result.error;
                messageDiv.classList.add('error');
            }
        } catch (error) {
            messageDiv.textContent = 'Network error occurred.';
            messageDiv.classList.add('error');
        }
    });

});
