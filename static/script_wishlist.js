  
        let wishlistData = [];

        function initializeWishlist() {
            const cards = document.querySelectorAll('.product-card');
            wishlistData = Array.from(cards).map(card => ({
                element: card,
                price: parseFloat(card.dataset.price),
                name: card.dataset.name,
                rating: parseFloat(card.dataset.rating)
            }));
            
            updateStats();
            
            if (wishlistData.length > 0) {
                document.getElementById('filterSort').style.display = 'flex';
                document.getElementById('productGrid').style.display = 'grid';
                document.getElementById('emptyWishlist').style.display = 'none';
            }
        }

        function removeFromWishlist(button, productId) {
            const card = button.closest('.product-card');
            const title = card.querySelector('.product-title').textContent;
            
            // Make API call to remove from wishlist
            fetch(`/api/wishlist/remove/${productId}`, {
                method: 'DELETE',
                headers: {
                    'Content-Type': 'application/json',
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Remove from local data
                    wishlistData = wishlistData.filter(item => item.element !== card);
                    
                    // Animate removal
                    card.classList.add('remove-animation');
                    
                    setTimeout(() => {
                        card.remove();
                        updateStats();
                        showNotification(data.message, 'success');
                        
                        if (wishlistData.length === 0) {
                            showEmptyState();
                        }
                    }, 600);
                } else {
                    showNotification(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error removing item from wishlist', 'error');
            });
        }

        function clearAllWishlist() {
            if (wishlistData.length === 0) return;
            
            if (confirm('Are you sure you want to clear your entire wishlist?')) {
                fetch('/api/wishlist/clear', {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json',
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        wishlistData.forEach(item => {
                            item.element.classList.add('remove-animation');
                        });
                        
                        setTimeout(() => {
                            wishlistData = [];
                            updateStats();
                            showEmptyState();
                            showNotification(data.message, 'success');
                        }, 600);
                    } else {
                        showNotification(data.message, 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('Error clearing wishlist', 'error');
                });
            }
        }

        function sortWishlist() {
            const sortBy = document.getElementById('sortBy').value;
            const grid = document.getElementById('productGrid');
            
            let sortedData = [...wishlistData];
            
            switch(sortBy) {
                case 'price-low':
                    sortedData.sort((a, b) => a.price - b.price);
                    break;
                case 'price-high':
                    sortedData.sort((a, b) => b.price - a.price);
                    break;
                case 'rating':
                    sortedData.sort((a, b) => b.rating - a.rating);
                    break;
                case 'name':
                    sortedData.sort((a, b) => a.name.localeCompare(b.name));
                    break;
            }
            
            sortedData.forEach(item => {
                grid.appendChild(item.element);
            });
        }

        function filterWishlist() {
            const filterPrice = document.getElementById('filterPrice').value;
            
            wishlistData.forEach(item => {
                let show = true;
                
                if (filterPrice !== 'all') {
                    const price = item.price;
                    switch(filterPrice) {
                        case '0-100':
                            show = price <= 100;
                            break;
                        case '100-300':
                            show = price > 100 && price <= 300;
                            break;
                        case '300-500':
                            show = price > 300 && price <= 500;
                            break;
                        case '500+':
                            show = price > 500;
                            break;
                    }
                }
                
                item.element.style.display = show ? 'block' : 'none';
            });
        }

        function updateStats() {
            const visibleItems = wishlistData.filter(item => item.element.style.display !== 'none');
            const itemCount = wishlistData.length;
            const totalValue = wishlistData.reduce((sum, item) => sum + item.price, 0);
            const avgPrice = itemCount > 0 ? totalValue / itemCount : 0;

            document.getElementById('itemCount').textContent = itemCount;
            document.getElementById('totalValue').textContent = `RM${totalValue.toFixed(2)}`;
            document.getElementById('avgPrice').textContent = `RM${avgPrice.toFixed(2)}`;
        }

        function showEmptyState() {
            document.getElementById('productGrid').style.display = 'none';
            document.getElementById('filterSort').style.display = 'none';
            document.getElementById('emptyWishlist').style.display = 'block';
        }

        function showNotification(message, type = 'success') {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = `notification ${type}`;
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3500);
        }

        // Initialize wishlist on page load
        document.addEventListener('DOMContentLoaded', initializeWishlist);
