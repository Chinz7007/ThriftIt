
        function uploadProfilePicture() {
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) return;
            
            const formData = new FormData();
            formData.append('profile_picture', file);
            
            fetch('/api/upload_profile_picture', {
                method: 'POST',
                body: formData
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Update the profile picture in the UI
                    document.getElementById('profilePicture').src = data.new_image_url;
                    
                    // Update all profile pictures on the page
                    const allProfilePics = document.querySelectorAll('.profile-pic');
                    allProfilePics.forEach(pic => {
                        pic.src = data.new_image_url;
                    });
                    
                    showNotification(data.message, 'success');
                } else {
                    showNotification(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('Error uploading profile picture', 'error');
            });
        }
        
        function showNotification(message, type) {
            const notification = document.getElementById('notification');
            notification.textContent = message;
            notification.className = notification ${type};
            notification.classList.add('show');
            
            setTimeout(() => {
                notification.classList.remove('show');
            }, 3000);
        }
 