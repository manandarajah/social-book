# Future Architecture Recommendations

This document provides detailed recommendations for implementing design patterns and improving SOLID principles compliance in the social-site application.

## Repository Pattern Implementation

### Current State
Database operations are called directly throughout the codebase, making it difficult to test and maintain.

### Proposed Implementation

```python
# repositories/base_repository.py
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository interface for CRUD operations"""
    
    @abstractmethod
    def find_by_id(self, id: str) -> Optional[T]:
        """Find entity by ID"""
        pass
    
    @abstractmethod
    def find_all(self, filters: dict = None) -> List[T]:
        """Find all entities matching filters"""
        pass
    
    @abstractmethod
    def create(self, entity: T) -> T:
        """Create new entity"""
        pass
    
    @abstractmethod
    def update(self, id: str, updates: dict) -> bool:
        """Update existing entity"""
        pass
    
    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete entity by ID"""
        pass


# repositories/user_repository.py
from typing import Optional
from models.user import User
from db import get_db_users

class UserRepository(BaseRepository[User]):
    """Repository for user operations"""
    
    def find_by_id(self, id: str) -> Optional[User]:
        """Find user by ID"""
        user_doc = get_db_users('read').find_one({'_id': ObjectId(id)})
        return User.from_dict(user_doc) if user_doc else None
    
    def find_by_username(self, username: str) -> Optional[User]:
        """Find user by username"""
        user_doc = get_db_users('read').find_one({'username': username})
        return User.from_dict(user_doc) if user_doc else None
    
    def find_by_email(self, email: str) -> Optional[User]:
        """Find user by email"""
        user_doc = get_db_users('read').find_one({'email': email})
        return User.from_dict(user_doc) if user_doc else None
    
    def create(self, user: User) -> User:
        """Create new user"""
        result = get_db_users('write').insert_one(user.to_dict())
        user.id = str(result.inserted_id)
        return user
    
    def update(self, id: str, updates: dict) -> bool:
        """Update user"""
        result = get_db_users('write').update_one(
            {'_id': ObjectId(id)}, 
            {'$set': updates}
        )
        return result.modified_count > 0
    
    def delete(self, id: str) -> bool:
        """Delete user"""
        result = get_db_users('write').delete_one({'_id': ObjectId(id)})
        return result.deleted_count > 0


# Usage in routes
def login():
    user_repo = UserRepository()
    user = user_repo.find_by_username(username)
    # ... rest of login logic
```

### Benefits
- **Testability**: Easy to mock repositories in unit tests
- **Flexibility**: Can swap database implementations
- **Maintainability**: Database logic centralized
- **SOLID**: Follows Single Responsibility and Dependency Inversion

## Service Layer Pattern

### Current State
Business logic is mixed with route handlers, making it difficult to reuse and test.

### Proposed Implementation

```python
# services/authentication_service.py
from repositories.user_repository import UserRepository
from argon2 import PasswordHasher
import logging

logger = logging.getLogger(__name__)

class AuthenticationService:
    """Service for authentication operations"""
    
    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo
        self.ph = PasswordHasher()
    
    def authenticate(self, identifier: str, password: str) -> tuple:
        """
        Authenticate user with username/email and password
        
        Returns:
            (success: bool, user: Optional[User], error: Optional[str])
        """
        # Find user by username or email
        user = self.user_repo.find_by_username(identifier)
        if not user:
            user = self.user_repo.find_by_email(identifier)
        
        if not user:
            logger.warning(f"Login attempt for non-existent user: {identifier}")
            return False, None, "Invalid credentials"
        
        # Verify password
        try:
            self.ph.verify(user.password_hash, password)
        except Exception:
            logger.warning(f"Failed login attempt for user: {user.username}")
            return False, None, "Invalid credentials"
        
        # Check if password needs rehashing
        if self.ph.check_needs_rehash(user.password_hash):
            new_hash = self.ph.hash(password)
            self.user_repo.update(user.id, {'password_hash': new_hash})
        
        logger.info(f"User authenticated: {user.username}")
        return True, user, None
    
    def register_user(self, user_data: dict) -> tuple:
        """
        Register new user
        
        Returns:
            (success: bool, user: Optional[User], error: Optional[str])
        """
        # Validate user doesn't exist
        if self.user_repo.find_by_username(user_data['username']):
            return False, None, "Username already exists"
        
        if self.user_repo.find_by_email(user_data['email']):
            return False, None, "Email already exists"
        
        # Hash password
        user_data['password_hash'] = self.ph.hash(user_data.pop('password'))
        
        # Create user
        user = User.from_dict(user_data)
        created_user = self.user_repo.create(user)
        
        logger.info(f"New user registered: {created_user.username}")
        return True, created_user, None


# Usage in routes
def login():
    auth_service = AuthenticationService(UserRepository())
    success, user, error = auth_service.authenticate(identifier, password)
    
    if not success:
        return render_template('login-form.html', err=error), 401
    
    login_user(user)
    return redirect('/')
```

### Benefits
- **Reusability**: Business logic can be used in multiple routes
- **Testability**: Easy to unit test without Flask context
- **Maintainability**: Clear separation of concerns
- **SOLID**: Single Responsibility Principle

## Strategy Pattern for File Storage

### Current State
File storage is tightly coupled to GridFS.

### Proposed Implementation

```python
# storage/storage_strategy.py
from abc import ABC, abstractmethod
from typing import BinaryIO

class FileStorageStrategy(ABC):
    """Abstract strategy for file storage"""
    
    @abstractmethod
    def store(self, file_data: bytes, filename: str, content_type: str) -> str:
        """Store file and return identifier"""
        pass
    
    @abstractmethod
    def retrieve(self, file_id: str) -> tuple:
        """Retrieve file and return (data, content_type)"""
        pass
    
    @abstractmethod
    def delete(self, file_id: str) -> bool:
        """Delete file"""
        pass


# storage/gridfs_storage.py
from datetime import datetime
from db import get_db_file

class GridFSStorage(FileStorageStrategy):
    """GridFS implementation of file storage"""
    
    def store(self, file_data: bytes, filename: str, content_type: str) -> str:
        file_id = get_db_file('write').put(
            file_data,
            filename=filename,
            content_type=content_type,
            upload_date=datetime.utcnow()
        )
        return str(file_id)
    
    def retrieve(self, file_id: str) -> tuple:
        file = get_db_file('read').get(ObjectId(file_id))
        return file.read(), file.content_type
    
    def delete(self, file_id: str) -> bool:
        get_db_file('write').delete(ObjectId(file_id))
        return True


# storage/s3_storage.py
import boto3

class S3Storage(FileStorageStrategy):
    """S3 implementation of file storage"""
    
    def __init__(self, bucket_name: str):
        self.s3 = boto3.client('s3')
        self.bucket = bucket_name
    
    def store(self, file_data: bytes, filename: str, content_type: str) -> str:
        key = f"{uuid.uuid4()}_{filename}"
        self.s3.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=file_data,
            ContentType=content_type
        )
        return key
    
    def retrieve(self, file_id: str) -> tuple:
        response = self.s3.get_object(Bucket=self.bucket, Key=file_id)
        return response['Body'].read(), response['ContentType']
    
    def delete(self, file_id: str) -> bool:
        self.s3.delete_object(Bucket=self.bucket, Key=file_id)
        return True


# services/file_service.py
class FileService:
    """Service for file operations"""
    
    def __init__(self, storage_strategy: FileStorageStrategy):
        self.storage = storage_strategy
    
    def upload_file(self, file: FileStorage) -> tuple:
        """Upload file with validation"""
        # ... validation logic ...
        file_id = self.storage.store(file_data, filename, mime_type)
        return True, file_id, None


# Configuration
storage_strategy = GridFSStorage()  # or S3Storage('bucket-name')
file_service = FileService(storage_strategy)
```

### Benefits
- **Flexibility**: Easy to switch storage backends
- **Testability**: Can use in-memory storage for tests
- **Extensibility**: Add new storage without modifying existing code
- **SOLID**: Open/Closed Principle

## Factory Pattern for User Creation

### Proposed Implementation

```python
# factories/user_factory.py
from models.user import User
from argon2 import PasswordHasher

class UserFactory:
    """Factory for creating user objects"""
    
    def __init__(self):
        self.ph = PasswordHasher()
    
    def create_from_registration(self, form_data: dict) -> User:
        """Create user from registration form"""
        user = User(
            username=form_data['username'].lower(),
            email=form_data['email'].lower(),
            password_hash=self.ph.hash(form_data['password']),
            first_name=form_data['first_name'],
            last_name=form_data['last_name'],
            gender=form_data['gender'],
            birthday=form_data['birthday'],
            is_verified=False
        )
        return user
    
    def create_from_dict(self, data: dict) -> User:
        """Create user from dictionary"""
        return User(**data)
    
    def create_test_user(self, username: str = "testuser") -> User:
        """Create user for testing"""
        return User(
            username=username,
            email=f"{username}@test.com",
            password_hash=self.ph.hash("TestPass123!"),
            first_name="Test",
            last_name="User",
            gender="other",
            birthday="2000-01-01",
            is_verified=True
        )
```

### Benefits
- **Encapsulation**: User creation logic centralized
- **Testability**: Easy to create test users
- **Consistency**: Ensures users are created correctly
- **Maintainability**: Single place to update user creation

## Dependency Injection Container

### Proposed Implementation

```python
# container.py
from typing import Dict, Callable, Any

class Container:
    """Simple dependency injection container"""
    
    def __init__(self):
        self._services: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, name: str, factory: Callable, singleton: bool = False):
        """Register a service factory"""
        self._services[name] = factory
        if singleton:
            self._singletons[name] = None
    
    def get(self, name: str) -> Any:
        """Get service instance"""
        if name in self._singletons:
            if self._singletons[name] is None:
                self._singletons[name] = self._services[name]()
            return self._singletons[name]
        
        return self._services[name]()
    
    def resolve(self, cls: type) -> Any:
        """Resolve dependencies and create instance"""
        # Simple implementation - can be enhanced
        return cls()


# Setup
container = Container()

# Register services
container.register('user_repo', lambda: UserRepository(), singleton=True)
container.register('post_repo', lambda: PostRepository(), singleton=True)
container.register('auth_service', lambda: AuthenticationService(
    container.get('user_repo')
), singleton=True)


# Usage
def login():
    auth_service = container.get('auth_service')
    # ... use service
```

### Benefits
- **Testability**: Easy to swap dependencies in tests
- **Maintainability**: Centralized dependency configuration
- **Flexibility**: Easy to change implementations
- **SOLID**: Dependency Inversion Principle

## Model Layer

### Proposed Implementation

```python
# models/user.py
from dataclasses import dataclass, asdict
from typing import Optional
from datetime import date

@dataclass
class User:
    """User domain model"""
    username: str
    email: str
    password_hash: str
    first_name: str
    last_name: str
    gender: str
    birthday: date
    is_verified: bool = False
    profile_picture: Optional[str] = None
    id: Optional[str] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for database"""
        data = asdict(self)
        if self.id:
            data['_id'] = ObjectId(self.id)
            del data['id']
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create from database dictionary"""
        if '_id' in data:
            data['id'] = str(data['_id'])
            del data['_id']
        return cls(**data)
    
    @property
    def full_name(self) -> str:
        """Get full name"""
        return f"{self.first_name} {self.last_name}"
    
    def can_post(self) -> bool:
        """Check if user can create posts"""
        return self.is_verified


# models/post.py
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class Post:
    """Post domain model"""
    username: str
    content: str
    created_at: datetime
    likes: List[str]
    comments: List[dict]
    attachment: Optional[str] = None
    id: Optional[str] = None
    
    def add_like(self, username: str):
        """Add like from user"""
        if username not in self.likes:
            self.likes.append(username)
    
    def remove_like(self, username: str):
        """Remove like from user"""
        if username in self.likes:
            self.likes.remove(username)
    
    def add_comment(self, username: str, content: str):
        """Add comment to post"""
        comment = {
            'username': username,
            'content': content,
            'created_at': datetime.now(timezone.utc)
        }
        self.comments.append(comment)
```

### Benefits
- **Type Safety**: Clear data structures
- **Encapsulation**: Business rules in models
- **Maintainability**: Single source of truth for data structure
- **Testability**: Easy to create test objects

## Implementation Roadmap

### Phase 1: Foundation (Week 1-2)
1. Create model classes (User, Post)
2. Implement base repository interface
3. Create UserRepository and PostRepository
4. Add unit tests for repositories

### Phase 2: Service Layer (Week 3-4)
1. Implement AuthenticationService
2. Implement PostService
3. Implement EmailService
4. Add unit tests for services

### Phase 3: Refactor Routes (Week 5-6)
1. Refactor authentication routes to use services
2. Refactor post routes to use services
3. Update error handling
4. Add integration tests

### Phase 4: Advanced Patterns (Week 7-8)
1. Implement dependency injection container
2. Add Strategy pattern for file storage
3. Implement Factory pattern for object creation
4. Add comprehensive tests

### Phase 5: Polish (Week 9-10)
1. Add type hints throughout
2. Update documentation
3. Performance optimization
4. Security audit

## Migration Strategy

To avoid breaking existing functionality:

1. **Parallel Implementation**: Create new patterns alongside existing code
2. **Gradual Migration**: Migrate one route at a time
3. **Feature Flags**: Use flags to switch between old and new implementations
4. **Comprehensive Testing**: Test each migration step
5. **Rollback Plan**: Keep old code until new code is proven stable

## Conclusion

These architectural improvements will significantly enhance the codebase quality, maintainability, and adherence to SOLID principles. The proposed patterns are industry-standard and will make the application more scalable, testable, and easier to maintain.

The implementation should be done gradually to minimize risk and ensure stability. Each phase should include comprehensive testing and documentation updates.
