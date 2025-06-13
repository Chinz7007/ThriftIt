function toggleWishlist(starElement, productId) {
    const isInWishlist = starElement.classList.contains('active');

    if (isInWishlist) {
        // Remove from wishlist
        fetch(`/api/wishlist/remove/${productId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                starElement.classList.remove('active');
                starElement.textContent = '☆'; // hollow star
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error updating wishlist', 'error');
        });
    } else {
        // Add to wishlist
        fetch(`/api/wishlist/add/${productId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                starElement.classList.add('active');
                starElement.textContent = '★'; // filled star
                showNotification(data.message, 'success');
            } else {
                showNotification(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('Error updating wishlist', 'error');
        });
    }
}

function showNotification(message, type = 'success') {
    const existingNotification = document.getElementById('notification');
    if (existingNotification) {
        existingNotification.remove();
    }

    const notification = document.createElement('div');
    notification.id = 'notification';
    notification.className = `notification ${type}`;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 400);
    }, 3500);
}

document.addEventListener('DOMContentLoaded', function() {
    const starElement = document.querySelector('.fav-star[data-product-id]');
    if (starElement) {
        const productId = starElement.getAttribute('data-product-id');

        fetch(`/api/wishlist/check/${productId}`)
            .then(response => response.json())
            .then(data => {
                if (data.in_wishlist) {
                    starElement.classList.add('active');
                    starElement.textContent = '★'; // filled star
                } else {
                    starElement.classList.remove('active');
                    starElement.textContent = '☆'; // hollow star
                }
            })
            .catch(error => {
                console.error('Error checking wishlist status:', error);
                starElement.textContent = '☆';
            });
    }
});
