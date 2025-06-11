#!/usr/bin/env python3
"""
Database initialization script for ThriftIt
Run this script to set up the database with sample data
"""

from app import app, db, User, Product, Message, Wishlist
from werkzeug.security import generate_password_hash
import os

def init_database():
    """Initialize database with tables and sample data"""
    
    with app.app_context():
        # Drop all tables and recreate them
        print("Creating database tables...")
        db.drop_all()
        db.create_all()
        
        # Create sample users
        print("Creating sample users...")
        users_data = [
            {
                'student_id': 'U2020001',
                'student_email': 'john.doe@university.edu',
                'password': 'password123',
                'full_name': 'John Doe'
            },
            {
                'student_id': 'U2020002', 
                'student_email': 'jane.smith@university.edu',
                'password': 'password123',
                'full_name': 'Jane Smith'
            },
            {
                'student_id': 'U2020003',
                'student_email': 'mike.johnson@university.edu', 
                'password': 'password123',
                'full_name': 'Mike Johnson'
            }
        ]
        
        created_users = []
        for user_data in users_data:
            user = User(
                student_id=user_data['student_id'],
                student_email=user_data['student_email'],
                full_name=user_data['full_name']
            )
            user.set_password(user_data['password'])
            db.session.add(user)
            created_users.append(user)
        
        db.session.commit()
        print(f"Created {len(created_users)} users")
        
        # Create sample products
        print("Creating sample products...")
        products_data = [
            {
                'name': 'Calculus Textbook',
                'price': 50.00,
                'image': 'textbook1.jpg',
                'description': 'Used calculus textbook in good condition',
                'category': 'Books',
                'condition': 'Like New',
                'seller_id': created_users[0].id
            },
            {
                'name': 'Gaming Chair',
                'price': 150.00,
                'image': 'chair1.jpg', 
                'description': 'Comfortable gaming chair, barely used',
                'category': 'Others',
                'condition': 'Lightly Used',
                'seller_id': created_users[1].id
            },
            {
                'name': 'iPhone 12 Case',
                'price': 15.00,
                'image': 'case1.jpg',
                'description': 'Protective case for iPhone 12',
                'category': 'Tech',
                'condition': 'Brand New',
                'seller_id': created_users[2].id
            },
            {
                'name': 'Winter Jacket',
                'price': 80.00,
                'image': 'jacket1.jpg',
                'description': 'Warm winter jacket, size M',
                'category': 'Clothes',
                'condition': 'Well Used',
                'seller_id': created_users[0].id
            }
        ]
        
        created_products = []
        for product_data in products_data:
            product = Product(**product_data)
            db.session.add(product)
            created_products.append(product)
            
        db.session.commit()
        print(f"Created {len(created_products)} products")
        
        # Create sample messages
        print("Creating sample messages...")
        message1 = Message(
            content="Hi! Is the calculus textbook still available?",
            sender_id=created_users[1].id,
            receiver_id=created_users[0].id
        )
        message2 = Message(
            content="Yes, it's still available! When would you like to meet?",
            sender_id=created_users[0].id,
            receiver_id=created_users[1].id
        )
        
        db.session.add(message1)
        db.session.add(message2)
        db.session.commit()
        print("Created sample messages")
        
        # Create sample wishlist items
        print("Creating sample wishlist items...")
        wishlist1 = Wishlist(user_id=created_users[1].id, product_id=created_products[0].id)
        wishlist2 = Wishlist(user_id=created_users[2].id, product_id=created_products[1].id)
        
        db.session.add(wishlist1)
        db.session.add(wishlist2)
        db.session.commit()
        print("Created sample wishlist items")
        
        print("\n✅ Database initialized successfully!")
        print("\nSample login credentials:")
        for user_data in users_data:
            print(f"Student ID: {user_data['student_id']}, Password: {user_data['password']}")

if __name__ == "__main__":
    # Create uploads directory if it doesn't exist
    uploads_dir = os.path.join(os.path.dirname(__file__), 'uploads')
    os.makedirs(uploads_dir, exist_ok=True)
    
    # Create default avatar if it doesn't exist
    default_avatar_path = os.path.join(uploads_dir, 'default-avatar.png')
    if not os.path.exists(default_avatar_path):
        print("Note: Place a 'default-avatar.png' file in the uploads folder for default profile pictures")
    
    init_database()