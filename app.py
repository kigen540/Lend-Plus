{% extends "base.html" %}

{% block title %}Loan Amount - LendPlus{% endblock %}

{% block content %}
<div class="form-container">
    <div class="progress-bar">
        <div class="fill" style="width: 100%;"></div>
    </div>
    <div class="progress-text">Step 3 of 3</div>
    
    <h2>{{ country_data.flag }} How much do you need?</h2>
    <p>Choose an amount between {{ currency_symbol }} {{ "{:,.0f}".format(min_loan) }} and {{ currency_symbol }} {{ "{:,.0f}".format(max_loan) }}</p>
    
    {% if error %}
    <div class="alert error">{{ error }}</div>
    {% endif %}
    
    <form method="POST" action="{{ url_for('loan_amount') }}">
        <div class="amount-options">
            <button type="button" class="amount-btn" onclick="setAmount({{ min_loan }})">
                {{ currency_symbol }} {{ "{:,.0f}".format(min_loan) }}
            </button>
            <button type="button" class="amount-btn" onclick="setAmount({{ (min_loan + max_loan) // 3 }})">
                {{ currency_symbol }} {{ "{:,.0f}".format((min_loan + max_loan) // 3) }}
            </button>
            <button type="button" class="amount-btn" onclick="setAmount({{ (max_loan + min_loan) // 2 }})">
                {{ currency_symbol }} {{ "{:,.0f}".format((max_loan + min_loan) // 2) }}
            </button>
            <button type="button" class="amount-btn" onclick="setAmount({{ max_loan }})">
                {{ currency_symbol }} {{ "{:,.0f}".format(max_loan) }}
            </button>
        </div>
        
        <div class="custom-amount">
            <label><strong>Or enter custom amount</strong></label>
            <input type="number" name="loan_amount" id="loan_amount" 
                   placeholder="Enter amount" min="{{ min_loan }}" max="{{ max_loan }}" 
                   value="{{ request.form.loan_amount or '' }}" required>
        </div>
        
        <div class="loan-info">
            <div class="info-row">
                <span>Application Fee:</span>
                <span><span id="fee_display">5</span>%</span>
            </div>
            <div class="info-row">
                <span>Repayment period:</span>
                <span><span id="months_display">1</span> month(s)</span>
            </div>
        </div>
        
        <button type="submit" class="btn-primary">Apply Now</button>
    </form>
</div>

<script>
    const loanInput = document.getElementById('loan_amount');
    const feeDisplay = document.getElementById('fee_display');
    const monthsDisplay = document.getElementById('months_display');
    const country = '{{ session.get("country", "kenya") }}';
    
    function getLoanTerms(amount, country) {
        let fee = 5, months = 1;
        
        if (country === 'kenya') {
            if (amount > 30000) { fee = 12; months = 6; }
            else if (amount > 10000) { fee = 8; months = 3; }
        } else if (country === 'uganda') {
            if (amount > 1000000) { fee = 12; months = 6; }
            else if (amount > 500000) { fee = 8; months = 3; }
        } else { // tanzania
            if (amount > 300000) { fee = 12; months = 6; }
            else if (amount > 100000) { fee = 8; months = 3; }
        }
        
        return { fee, months };
    }
    
    loanInput.addEventListener('input', function() {
        const amount = parseInt(this.value) || 0;
        const terms = getLoanTerms(amount, country);
        
        feeDisplay.textContent = terms.fee;
        monthsDisplay.textContent = terms.months;
    });
    
    function setAmount(amount) {
        document.getElementById('loan_amount').value = amount;
        const event = new Event('input');
        loanInput.dispatchEvent(event);
        document.querySelectorAll('.amount-btn').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
    }
</script>
{% endblock %}