// ZebEduApplication JavaScript

// Auto-hide alerts after 5 seconds
document.addEventListener('DOMContentLoaded', function() {
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });
});

// Form validation
function validateForm(formId) {
    const form = document.getElementById(formId);
    if (!form.checkValidity()) {
        form.classList.add('was-validated');
        return false;
    }
    return true;
}

// Password strength checker
function checkPasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (password.match(/[a-z]+/)) strength++;
    if (password.match(/[A-Z]+/)) strength++;
    if (password.match(/[0-9]+/)) strength++;
    if (password.match(/[$@#&!]+/)) strength++;
    
    return strength;
}

// Display password strength
if (document.getElementById('password')) {
    document.getElementById('password').addEventListener('keyup', function() {
        const password = this.value;
        const strength = checkPasswordStrength(password);
        
        let strengthText = '';
        let strengthClass = '';
        
        switch(strength) {
            case 0:
            case 1:
                strengthText = 'Weak';
                strengthClass = 'text-danger';
                break;
            case 2:
            case 3:
                strengthText = 'Medium';
                strengthClass = 'text-warning';
                break;
            case 4:
            case 5:
                strengthText = 'Strong';
                strengthClass = 'text-success';
                break;
        }
        
        // Create or update strength indicator
        let indicator = document.getElementById('passwordStrength');
        if (!indicator && password.length > 0) {
            indicator = document.createElement('small');
            indicator.id = 'passwordStrength';
            indicator.className = 'form-text';
            this.parentElement.appendChild(indicator);
        }
        
        if (indicator) {
            if (password.length === 0) {
                indicator.remove();
            } else {
                indicator.className = 'form-text ' + strengthClass;
                indicator.textContent = 'Password Strength: ' + strengthText;
            }
        }
    });
}

// Confirm password validation
if (document.getElementById('confirm_password')) {
    document.getElementById('confirm_password').addEventListener('keyup', function() {
        const password = document.getElementById('password').value;
        const confirmPassword = this.value;
        
        let feedback = document.getElementById('passwordMatch');
        if (!feedback) {
            feedback = document.createElement('small');
            feedback.id = 'passwordMatch';
            feedback.className = 'form-text';
            this.parentElement.appendChild(feedback);
        }
        
        if (confirmPassword.length === 0) {
            feedback.remove();
        } else if (password === confirmPassword) {
            feedback.className = 'form-text text-success';
            feedback.textContent = '✓ Passwords match';
        } else {
            feedback.className = 'form-text text-danger';
            feedback.textContent = '✗ Passwords do not match';
        }
    });
}

// ID Number validation (South African ID)
if (document.getElementById('id_number')) {
    document.getElementById('id_number').addEventListener('blur', function() {
        const idNumber = this.value;
        
        if (idNumber.length === 13 && /^\d+$/.test(idNumber)) {
            // Basic SA ID validation
            const year = idNumber.substring(0, 2);
            const month = idNumber.substring(2, 4);
            const day = idNumber.substring(4, 6);
            
            if (month < 1 || month > 12 || day < 1 || day > 31) {
                this.setCustomValidity('Invalid ID number');
                this.classList.add('is-invalid');
            } else {
                this.setCustomValidity('');
                this.classList.remove('is-invalid');
                this.classList.add('is-valid');
            }
        } else if (idNumber.length > 0) {
            this.setCustomValidity('ID number must be 13 digits');
            this.classList.add('is-invalid');
        }
    });
}

// Phone number formatting
if (document.getElementById('phone_number')) {
    document.getElementById('phone_number').addEventListener('input', function() {
        let value = this.value.replace(/\D/g, '');
        
        if (value.length > 10) {
            value = value.substring(0, 10);
        }
        
        this.value = value;
    });
}

// Smooth scroll to top
function scrollToTop() {
    window.scrollTo({
        top: 0,
        behavior: 'smooth'
    });
}

// Add scroll to top button
window.addEventListener('scroll', function() {
    let scrollBtn = document.getElementById('scrollTopBtn');
    
    if (window.pageYOffset > 300) {
        if (!scrollBtn) {
            scrollBtn = document.createElement('button');
            scrollBtn.id = 'scrollTopBtn';
            scrollBtn.className = 'btn btn-primary position-fixed';
            scrollBtn.style.cssText = 'bottom: 20px; right: 20px; z-index: 1000; border-radius: 50%; width: 50px; height: 50px;';
            scrollBtn.innerHTML = '<i class="fas fa-arrow-up"></i>';
            scrollBtn.onclick = scrollToTop;
            document.body.appendChild(scrollBtn);
        }
        scrollBtn.style.display = 'block';
    } else if (scrollBtn) {
        scrollBtn.style.display = 'none';
    }
});

// Loading spinner
function showLoading() {
    const spinner = document.createElement('div');
    spinner.id = 'loadingSpinner';
    spinner.className = 'position-fixed top-50 start-50 translate-middle';
    spinner.style.zIndex = '9999';
    spinner.innerHTML = `
        <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
        </div>
    `;
    document.body.appendChild(spinner);
}

function hideLoading() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.remove();
    }
}

// Print functionality
function printPage() {
    window.print();
}

// Export table to CSV
function exportTableToCSV(tableId, filename) {
    const table = document.getElementById(tableId);
    let csv = [];
    
    // Get headers
    const headers = [];
    table.querySelectorAll('thead th').forEach(th => {
        headers.push(th.textContent.trim());
    });
    csv.push(headers.join(','));
    
    // Get data
    table.querySelectorAll('tbody tr').forEach(tr => {
        const row = [];
        tr.querySelectorAll('td').forEach(td => {
            row.push('"' + td.textContent.trim().replace(/"/g, '""') + '"');
        });
        csv.push(row.join(','));
    });
    
    // Download
    const csvContent = csv.join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

// Confirmation dialog
function confirmAction(message) {
    return confirm(message);
}

// Toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer') || createToastContainer();
    
    const toast = document.createElement('div');
    toast.className = `toast align-items-center text-white bg-${type} border-0`;
    toast.setAttribute('role', 'alert');
    toast.setAttribute('aria-live', 'assertive');
    toast.setAttribute('aria-atomic', 'true');
    
    toast.innerHTML = `
        <div class="d-flex">
            <div class="toast-body">
                ${message}
            </div>
            <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
        </div>
    `;
    
    toastContainer.appendChild(toast);
    
    const bsToast = new bootstrap.Toast(toast);
    bsToast.show();
    
    toast.addEventListener('hidden.bs.toast', () => {
        toast.remove();
    });
}

function createToastContainer() {
    const container = document.createElement('div');
    container.id = 'toastContainer';
    container.className = 'toast-container position-fixed bottom-0 end-0 p-3';
    document.body.appendChild(container);
    return container;
}

// Console log for debugging
console.log('ZebEduApplication JavaScript Loaded Successfully');