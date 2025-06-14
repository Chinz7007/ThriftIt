const container = document.querySelector('.container');
const registerBtn = document.querySelector('.register-btn');
const loginBtn = document.querySelector('.login-btn');

registerBtn.addEventListener('click', () => {
    container.classList.add('active');
});

loginBtn.addEventListener('click', () => {
    container.classList.remove('active');
});

document.addEventListener('DOMContentLoaded', function() {
    const flashes = document.querySelectorAll('.flash');
    
    // Only show the last 2 flash messages
    if (flashes.length > 2) {
        for (let i = 0; i < flashes.length - 2; i++) {
            flashes[i].style.display = 'none';
        }
    }
    
    // Auto-hide after 5 seconds
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.animation = 'fadeOut 0.5s ease-out forwards';
        }, 5000);
    });
});