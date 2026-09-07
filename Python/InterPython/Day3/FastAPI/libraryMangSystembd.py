"""
Library Management System (LMS)
Zero-Bloat Pure Python 3.10+ Implementation
Structured Flowchart Architecture with Field Validations, Role Security, Auto-Increment IDs, and Password Auth
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from datetime import datetime, date, timedelta
from typing import Any, Callable, Optional, List, Dict, Tuple, TypeVar
from collections import Counter
from pathlib import Path
import json
import hashlib
import sys
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, Field


def hash_password(password: str) -> str:
    """Zero-dependency secure SHA-256 password hashing."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# =====================================================================
# STEP 1: DATA STRUCTURES & DOMAIN ENTITIES
# =====================================================================

@dataclass
class User:
    """Represents a library patron or administrative staff member."""
    user_id: str
    name: str
    email: str
    password_hash: str
    role: str = "patron"  # "patron" | "admin"
    phone: Optional[str] = None
    is_blocked: bool = False
    registered_at: str = field(default_factory=lambda: datetime.now().isoformat())
    notifications: List[str] = field(default_factory=list)


@dataclass
class Book:
    """Represents a cataloged title with physical copy tracking."""
    isbn: str
    title: str
    author: str
    total_copies: int = 1
    available_copies: int = 1
    category: str = "General"
    published_year: Optional[int] = None
    tags: List[str] = field(default_factory=list)


@dataclass
class LoanRecord:
    """Represents a circulation checkout event."""
    loan_id: str
    user_id: str
    isbn: str
    issue_date: str
    due_date: str
    loan_days: int
    return_status: str = "ISSUED"  # "ISSUED" | "PENDING_APPROVAL" | "RETURNED"
    return_date: Optional[str] = None
    approved_by_admin: Optional[str] = None
    fine_amount: float = 0.0


@dataclass
class Reservation:
    """Represents an active or historical hold placed on an out-of-stock book."""
    reservation_id: str
    user_id: str
    isbn: str
    requested_at: str
    status: str = "PENDING"  # "PENDING" | "NOTIFIED" | "FULFILLED" | "CANCELLED"


@dataclass
class LibraryReport:
    """Snapshot analytics of circulation and inventory status."""
    report_id: str
    generated_at: str
    total_users: int
    total_titles: int
    total_copies: int
    active_loans: int
    pending_returns: int
    overdue_loans: int
    active_reservations: int
    total_fines_assessed: float
    top_borrowed_isbns: List[Tuple[str, int]]


# =====================================================================
# STEP 2 & 3: CORE LIBRARY ENGINE
# =====================================================================

class LibrarySystem:
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.catalog: Dict[str, Book] = {}
        self.loans: Dict[str, LoanRecord] = {}
        self.reservations: List[Reservation] = []

        self._user_seq: int = 0
        self._admin_seq: int = 0
        self._patron_seq: int = 0
        self._loan_seq: int = 0
        self._reservation_seq: int = 0
        self._report_seq: int = 0

        self.daily_fine_rate: float = 0.50

    def _next_user_id(self, role: str = "patron") -> str:
        normalized_role = role.lower()
        if normalized_role == "admin":
            self._admin_seq += 1
            self._user_seq = max(self._user_seq, self._admin_seq)
            return f"A{self._admin_seq:03d}"

        self._patron_seq += 1
        self._user_seq = max(self._user_seq, self._patron_seq)
        return f"U{self._patron_seq:04d}"

    def _next_loan_id(self) -> str:
        self._loan_seq += 1
        return f"LN-{self._loan_seq:05d}"

    def _next_reservation_id(self) -> str:
        self._reservation_seq += 1
        return f"RES-{self._reservation_seq:05d}"

    def _next_report_id(self) -> str:
        self._report_seq += 1
        now_str = datetime.now().strftime("%Y%m%d")
        return f"RPT-{now_str}-{self._report_seq:03d}"

    @staticmethod
    def _validate_user_fields(name: str, email: str, role: str, phone: Optional[str] = None) -> None:
        if not isinstance(name, str) or not (2 <= len(name.strip()) <= 100):
            raise ValueError("User name must be a string between 2 and 100 characters.")
        
        email_clean = email.strip()
        if "@" not in email_clean:
            raise ValueError("Email must contain an '@' character.")
        parts = email_clean.split("@")
        if len(parts) != 2 or not parts[0] or "." not in parts[1]:
            raise ValueError("Email must be in a valid format (e.g., user@domain.com).")

        if role.lower() not in ("patron", "admin"):
            raise ValueError("Role must strictly be either 'patron' or 'admin'.")

        if phone:
            digits = "".join(c for c in phone if c.isdigit())
            if not (7 <= len(digits) <= 15):
                raise ValueError("Phone number must contain between 7 and 15 digits.")

    @staticmethod
    def _validate_book_fields(isbn: str, title: str, author: str, total_copies: int) -> str:
        clean_isbn = isbn.replace("-", "").replace(" ", "").upper().strip()
        if len(clean_isbn) not in (10, 13) or not clean_isbn[:9].isdigit():
            raise ValueError("ISBN must be valid ISBN-10 or ISBN-13 (10 or 13 digits/characters).")

        if not isinstance(title, str) or not title.strip() or len(title) > 200:
            raise ValueError("Book title must be a non-empty string under 200 characters.")

        if not isinstance(author, str) or not author.strip() or len(author) > 120:
            raise ValueError("Book author must be a non-empty string under 120 characters.")

        if not isinstance(total_copies, int) or total_copies < 1:
            raise ValueError("Total copies must be a positive integer >= 1.")

        return clean_isbn

    def register_user(
        self,
        name: str,
        email: str,
        password: str = "patron123",
        role: str = "patron",
        phone: Optional[str] = None
    ) -> User:
        self._validate_user_fields(name, email, role, phone)
        if len(password) < 4:
            raise ValueError("Password must be at least 4 characters long.")

        for existing in self.users.values():
            if existing.email.lower() == email.strip().lower():
                raise ValueError(f"Email '{email}' is already registered to user ID '{existing.user_id}'.")

        user_id = self._next_user_id(role)
        if user_id in self.users:
            raise ValueError(f"User ID '{user_id}' already exists in system.")

        user = User(
            user_id=user_id,
            name=name.strip(),
            email=email.strip().lower(),
            password_hash=hash_password(password),
            role=role.lower(),
            phone=phone.strip() if phone else None,
            is_blocked=False
        )
        self.users[user_id] = user
        return user

    def update_user_profile(
        self,
        user_id: str,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None
    ) -> User:
        if user_id not in self.users:
            raise KeyError(f"User '{user_id}' not found.")
        user = self.users[user_id]

        new_name = name.strip() if name else user.name
        new_email = email.strip().lower() if email else user.email
        new_phone = phone.strip() if phone is not None else user.phone

        self._validate_user_fields(new_name, new_email, user.role, new_phone)

        if new_email != user.email:
            for uid, existing in self.users.items():
                if uid != user_id and existing.email == new_email:
                    raise ValueError(f"Email '{new_email}' is already registered to user '{uid}'.")

        user.name = new_name
        user.email = new_email
        user.phone = new_phone
        return user

    def set_user_block_status(self, admin_user_id: str, target_user_id: str, blocked: bool) -> User:
        admin = self.users.get(admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError("Only an administrator can modify account block status.")

        if target_user_id not in self.users:
            raise KeyError(f"Target user '{target_user_id}' not found.")

        target = self.users[target_user_id]
        target.is_blocked = blocked
        action_verb = "blocked" if blocked else "unblocked"
        target.notifications.append(f"Account has been {action_verb} by admin {admin.name} on {datetime.now().strftime('%Y-%m-%d %H:%M')}.")
        return target

    def notify_user(self, user_id: str, message: str) -> None:
        if user_id not in self.users:
            raise KeyError(f"User '{user_id}' not found.")
        self.users[user_id].notifications.append(f"[{datetime.now().strftime('%Y-%m-%d %H:%M')}] {message}")

    def add_book(
        self,
        admin_user_id: str,
        isbn: str,
        title: str,
        author: str,
        total_copies: int = 1,
        category: str = "General",
        published_year: Optional[int] = None,
        tags: Optional[List[str]] = None
    ) -> Book:
        admin = self.users.get(admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError(f"Access Denied: User '{admin_user_id}' is not an authorized administrator.")

        clean_isbn = self._validate_book_fields(isbn, title, author, total_copies)
        if clean_isbn in self.catalog:
            raise ValueError(f"Book with ISBN '{clean_isbn}' already exists. Use update_book_copies() instead.")

        if published_year is not None:
            current_year = datetime.now().year
            if published_year < 1000 or published_year > current_year + 1:
                raise ValueError(f"Published year must be between 1000 and {current_year + 1}.")

        book = Book(
            isbn=clean_isbn,
            title=title.strip(),
            author=author.strip(),
            total_copies=total_copies,
            available_copies=total_copies,
            category=category.strip(),
            published_year=published_year,
            tags=[t.strip() for t in (tags or []) if t.strip()]
        )
        self.catalog[clean_isbn] = book
        return book

    def update_book_copies(self, admin_user_id: str, isbn: str, additional_copies: int) -> Book:
        admin = self.users.get(admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError("Access Denied: Only administrators may update catalog inventory.")

        clean_isbn = isbn.replace("-", "").replace(" ", "").upper().strip()
        if clean_isbn not in self.catalog:
            raise KeyError(f"Book with ISBN '{clean_isbn}' not found.")

        book = self.catalog[clean_isbn]
        new_total = book.total_copies + additional_copies
        if new_total < 1:
            raise ValueError(f"Cannot reduce total copies below 1 (Attempted new total: {new_total}).")

        new_avail = book.available_copies + additional_copies
        if new_avail < 0:
            raise ValueError("Cannot reduce available copies below 0 (Currently on loan).")

        book.total_copies = new_total
        book.available_copies = new_avail
        return book

    def checkout_book(self, user_id: str, isbn: str, loan_days: int = 14) -> LoanRecord:
        if user_id not in self.users:
            raise KeyError(f"User '{user_id}' does not exist.")
        user = self.users[user_id]

        if user.is_blocked:
            raise PermissionError(f"User '{user.name}' is blocked and cannot checkout books.")

        clean_isbn = isbn.replace("-", "").replace(" ", "").upper().strip()
        if clean_isbn not in self.catalog:
            raise KeyError(f"Book with ISBN '{clean_isbn}' does not exist in catalog.")
        book = self.catalog[clean_isbn]

        if book.available_copies <= 0:
            raise ValueError(f"'{book.title}' is currently out of stock. Please place a reservation instead.")

        if not (1 <= loan_days < 60):
            raise ValueError(f"Invalid loan duration ({loan_days} days). Due date must be strictly under 2 months (< 60 days).")

        now = datetime.now()
        due = now + timedelta(days=loan_days)
        loan_id = self._next_loan_id()

        loan = LoanRecord(
            loan_id=loan_id,
            user_id=user_id,
            isbn=clean_isbn,
            issue_date=now.strftime("%Y-%m-%d %H:%M"),
            due_date=due.strftime("%Y-%m-%d %H:%M"),
            loan_days=loan_days,
            return_status="ISSUED"
        )

        book.available_copies -= 1
        self.loans[loan_id] = loan
        self.notify_user(user_id, f"Checked out '{book.title}' (Loan ID: {loan_id}). Due by {loan.due_date}.")
        return loan

    def request_return(self, loan_id: str) -> LoanRecord:
        if loan_id not in self.loans:
            raise KeyError(f"Loan record '{loan_id}' not found.")

        loan = self.loans[loan_id]
        if loan.return_status == "RETURNED":
            raise ValueError(f"Loan '{loan_id}' has already been processed and closed.")
        if loan.return_status == "PENDING_APPROVAL":
            raise ValueError(f"Loan '{loan_id}' is already pending administrator review.")

        loan.return_status = "PENDING_APPROVAL"
        loan.return_date = datetime.now().strftime("%Y-%m-%d %H:%M")
        return loan

    def place_reservation(self, user_id: str, isbn: str) -> Reservation:
        if user_id not in self.users:
            raise KeyError(f"User '{user_id}' does not exist.")
        user = self.users[user_id]

        if user.is_blocked:
            raise PermissionError(f"User '{user.name}' is blocked and cannot place reservations.")

        clean_isbn = isbn.replace("-", "").replace(" ", "").upper().strip()
        if clean_isbn not in self.catalog:
            raise KeyError(f"Book with ISBN '{clean_isbn}' not found in catalog.")
        book = self.catalog[clean_isbn]

        if book.available_copies > 0:
            raise ValueError(f"'{book.title}' currently has {book.available_copies} copy available. Please checkout directly.")

        active_holds = [
            r for r in self.reservations
            if r.user_id == user_id and r.status in ("PENDING", "NOTIFIED")
        ]
        if len(active_holds) >= 3:
            raise ValueError(f"Reservation limit reached: Patron '{user.name}' already has {len(active_holds)} active reservations (Max 3 allowed).")

        for hold in active_holds:
            if hold.isbn == clean_isbn:
                raise ValueError(f"Patron '{user.name}' already has an active reservation for ISBN '{clean_isbn}'.")

        res_id = self._next_reservation_id()
        reservation = Reservation(
            reservation_id=res_id,
            user_id=user_id,
            isbn=clean_isbn,
            requested_at=datetime.now().strftime("%Y-%m-%d %H:%M"),
            status="PENDING"
        )
        self.reservations.append(reservation)
        self.notify_user(user_id, f"Placed hold on '{book.title}' (Hold ID: {res_id}). Position in queue: {len(self.reservations)}.")
        return reservation

    def approve_return_and_assess(
        self,
        admin_user_id: str,
        loan_id: str,
        damaged: bool = False,
        damage_fee: float = 0.0
    ) -> Tuple[LoanRecord, float]:
        admin = self.users.get(admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError("Access Denied: Only administrators can inspect and approve book returns.")

        if loan_id not in self.loans:
            raise KeyError(f"Loan record '{loan_id}' not found.")

        loan = self.loans[loan_id]
        if loan.return_status == "RETURNED":
            raise ValueError(f"Loan '{loan_id}' is already finalized and closed.")

        due_dt = datetime.strptime(loan.due_date, "%Y-%m-%d %H:%M")
        now_dt = datetime.now()
        overdue_days = max(0, (now_dt - due_dt).days)
        overdue_fine = overdue_days * self.daily_fine_rate
        total_fine = overdue_fine + (damage_fee if damaged else 0.0)

        loan.return_status = "RETURNED"
        loan.approved_by_admin = admin_user_id
        loan.fine_amount = total_fine
        if not loan.return_date:
            loan.return_date = now_dt.strftime("%Y-%m-%d %H:%M")

        book = self.catalog[loan.isbn]
        book.available_copies = min(book.total_copies, book.available_copies + 1)

        fine_msg = f" Overdue fine assessed: USD {total_fine:.2f}." if total_fine > 0 else " No fines assessed."
        self.notify_user(loan.user_id, f"Your return for '{book.title}' (Loan {loan_id}) was approved by Admin {admin.name}.{fine_msg}")

        for res in self.reservations:
            if res.isbn == loan.isbn and res.status == "PENDING":
                res.status = "NOTIFIED"
                self.notify_user(res.user_id, f"Good news! Reserved book '{book.title}' is now available for checkout. Claim Hold ID: {res.reservation_id}.")
                break

        return loan, total_fine

    def generate_system_report(self) -> LibraryReport:
        now_dt = datetime.now()
        total_users = len(self.users)
        total_titles = len(self.catalog)
        total_copies = sum(b.total_copies for b in self.catalog.values())
        active_loans = sum(1 for l in self.loans.values() if l.return_status == "ISSUED")
        pending_returns = sum(1 for l in self.loans.values() if l.return_status == "PENDING_APPROVAL")
        
        overdue_count = 0
        for l in self.loans.values():
            if l.return_status in ("ISSUED", "PENDING_APPROVAL"):
                due_dt = datetime.strptime(l.due_date, "%Y-%m-%d %H:%M")
                if now_dt > due_dt:
                    overdue_count += 1

        active_res = sum(1 for r in self.reservations if r.status in ("PENDING", "NOTIFIED"))
        total_fines = sum(l.fine_amount for l in self.loans.values())
        loan_counts = Counter(l.isbn for l in self.loans.values())
        top_borrowed = loan_counts.most_common(5)

        return LibraryReport(
            report_id=self._next_report_id(),
            generated_at=now_dt.strftime("%Y-%m-%d %H:%M"),
            total_users=total_users,
            total_titles=total_titles,
            total_copies=total_copies,
            active_loans=active_loans,
            pending_returns=pending_returns,
            overdue_loans=overdue_count,
            active_reservations=active_res,
            total_fines_assessed=round(total_fines, 2),
            top_borrowed_isbns=top_borrowed
        )

    def backup_to_json(self, filepath: str = "library_backup.json") -> str:
        state = {
            "metadata": {
                "system": "LibraryManagementSystem",
                "version": "1.0",
                "exported_at": datetime.now().isoformat(),
                "counters": {
                    "user_seq": self._user_seq,
                    "loan_seq": self._loan_seq,
                    "reservation_seq": self._reservation_seq,
                    "report_seq": self._report_seq,
                }
            },
            "users": {uid: asdict(u) for uid, u in self.users.items()},
            "catalog": {isbn: asdict(b) for isbn, b in self.catalog.items()},
            "loans": {lid: asdict(l) for lid, l in self.loans.items()},
            "reservations": [asdict(r) for r in self.reservations],
        }
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return filepath


# =====================================================================
# DEMO DATA SEEDER
# =====================================================================

def seed_demo_data(system: LibrarySystem) -> None:
    admin = system.register_user(
        name="Chief Librarian Eleanor Vance",
        email="eleanor@citylibrary.org",
        password="admin123",
        role="admin",
        phone="+1-555-0100"
    )
    system.register_user(name="Ada Lovelace", email="ada@computing.org", password="patron123", role="patron", phone="+1-555-0101")
    system.register_user(name="Alan Turing", email="alan@enigma.org", password="patron123", role="patron", phone="+1-555-0102")
    system.register_user(name="Grace Hopper", email="grace@navy.mil", password="patron123", role="patron", phone="+1-555-0103")

    admin_id = admin.user_id
    system.add_book(
        admin_user_id=admin_id,
        isbn="978-0132350884",
        title="Clean Code: A Handbook of Agile Software Craftsmanship",
        author="Robert C. Martin",
        total_copies=3,
        category="Computer Science",
        published_year=2008,
        tags=["Architecture", "Best Practices", "Refactoring"]
    )
    system.add_book(
        admin_user_id=admin_id,
        isbn="978-0201616224",
        title="The Pragmatic Programmer: Your Journey to Mastery",
        author="David Thomas, Andrew Hunt",
        total_copies=2,
        category="Computer Science",
        published_year=1999,
        tags=["Career", "Craftsmanship", "Productivity"]
    )
    system.add_book(
        admin_user_id=admin_id,
        isbn="978-0262033848",
        title="Introduction to Algorithms (CLRS)",
        author="Thomas H. Cormen et al.",
        total_copies=1,
        category="Computer Science",
        published_year=2009,
        tags=["Algorithms", "Data Structures", "Theory"]
    )
    system.checkout_book("U0001", "978-0262033848", loan_days=21)


# =====================================================================
# FASTAPI ADAPTER
# =====================================================================

DATA_FILE = Path(__file__).with_name("libMangSys.json")
app = FastAPI(title="Library Management System API", version="1.0.0")
api_system = LibrarySystem()
T = TypeVar("T")


class LoginRequest(BaseModel):
    user_id: str
    password: str


class UserCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str
    password: str = Field(min_length=4)
    role: str = "patron"
    phone: Optional[str] = None


class UserUpdateRequest(BaseModel):
    name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[str] = None
    phone: Optional[str] = None


class BlockStatusRequest(BaseModel):
    admin_user_id: str
    blocked: bool


class BookCreateRequest(BaseModel):
    admin_user_id: str
    isbn: str
    title: str
    author: str
    total_copies: int = Field(default=1, ge=1)
    category: str = "General"
    published_year: Optional[int] = None
    tags: List[str] = Field(default_factory=list)


class BookCopiesRequest(BaseModel):
    admin_user_id: str
    additional_copies: int


class CheckoutRequest(BaseModel):
    user_id: str
    isbn: str
    loan_days: int = Field(default=14, ge=1, lt=60)


class ReservationRequest(BaseModel):
    user_id: str
    isbn: str


class ReturnApprovalRequest(BaseModel):
    admin_user_id: str
    damaged: bool = False
    damage_fee: float = Field(default=0.0, ge=0)


class BackupRequest(BaseModel):
    admin_user_id: str


def _state_as_dict() -> Dict[str, Any]:
    return {
        "metadata": {
            "system": "LibraryManagementSystem",
            "version": "1.0",
            "exported_at": datetime.now().isoformat(),
            "counters": {
                "user_seq": api_system._user_seq,
                "admin_seq": api_system._admin_seq,
                "patron_seq": api_system._patron_seq,
                "loan_seq": api_system._loan_seq,
                "reservation_seq": api_system._reservation_seq,
                "report_seq": api_system._report_seq,
            },
        },
        "users": {user_id: asdict(user) for user_id, user in api_system.users.items()},
        "catalog": {isbn: asdict(book) for isbn, book in api_system.catalog.items()},
        "loans": {loan_id: asdict(loan) for loan_id, loan in api_system.loans.items()},
        "reservations": [asdict(reservation) for reservation in api_system.reservations],
    }


def _save_state() -> None:
    DATA_FILE.write_text(json.dumps(_state_as_dict(), indent=2), encoding="utf-8")


def _load_state() -> None:
    if not DATA_FILE.exists():
        seed_demo_data(api_system)
        _save_state()
        return

    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    counters = data.get("metadata", {}).get("counters", {})
    api_system.users = {}
    for user_id, value in data.get("users", {}).items():
        user_data = dict(value)
        if "password_hash" not in user_data:
            default_password = "admin123" if user_data.get("role") == "admin" else "patron123"
            user_data["password_hash"] = hash_password(default_password)
        api_system.users[user_id] = User(**user_data)

    admin_ids = [int(user_id[1:]) for user_id in api_system.users if user_id.startswith("A")]
    patron_ids = [int(user_id[1:]) for user_id in api_system.users if user_id.startswith("U")]
    api_system._admin_seq = max(admin_ids, default=0)
    api_system._patron_seq = max(patron_ids, default=0)
    api_system._user_seq = max(api_system._admin_seq, api_system._patron_seq)
    api_system._loan_seq = counters.get("loan_seq", 0)
    api_system._reservation_seq = counters.get("reservation_seq", 0)
    api_system._report_seq = counters.get("report_seq", 0)
    api_system.catalog = {
        isbn: Book(**value) for isbn, value in data.get("catalog", {}).items()
    }
    api_system.loans = {
        loan_id: LoanRecord(**value)
        for loan_id, value in data.get("loans", {}).items()
    }
    api_system.reservations = [
        Reservation(**value) for value in data.get("reservations", [])
    ]


def _run_write(operation: Callable[[], T]) -> T:
    try:
        result = operation()
        _save_state()
        return result
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc).strip("'")) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.on_event("startup")
def load_json_data() -> None:
    try:
        _load_state()
        _save_state()
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        raise RuntimeError(f"Unable to load {DATA_FILE.name}: {exc}") from exc


@app.get("/")
def root() -> Dict[str, str]:
    return {"message": "Library Management System API", "docs": "/docs"}


@app.post("/auth/login", response_model=User)
def login(credentials: LoginRequest) -> User:
    ident = credentials.user_id.strip()
    user = api_system.users.get(ident)
    if not user:
        user = next((u for u in api_system.users.values() if u.email.lower() == ident.lower()), None)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid User ID or Email.")

    hashed_input = hash_password(credentials.password)
    if user.password_hash != hashed_input and user.password_hash != credentials.password:
        raise HTTPException(status_code=401, detail="Incorrect password.")

    if user.is_blocked:
        raise HTTPException(status_code=403, detail="Account is blocked. Contact administrator.")

    return user


@app.get("/users", response_model=List[User])
def list_users(role: Optional[str] = Query(default=None)) -> List[User]:
    users = list(api_system.users.values())
    return [user for user in users if role is None or user.role == role.lower()]


@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: str) -> User:
    user = api_system.users.get(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail=f"User '{user_id}' not found.")
    return user


@app.post("/users", response_model=User, status_code=201)
def create_user(request: UserCreateRequest) -> User:
    return _run_write(lambda: api_system.register_user(
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role,
        phone=request.phone,
    ))


@app.patch("/users/{user_id}", response_model=User)
def update_user(user_id: str, request: UserUpdateRequest) -> User:
    return _run_write(lambda: api_system.update_user_profile(
        user_id, name=request.name, email=request.email, phone=request.phone
    ))


@app.patch("/users/{user_id}/block", response_model=User)
def update_user_block_status(user_id: str, request: BlockStatusRequest) -> User:
    return _run_write(lambda: api_system.set_user_block_status(
        request.admin_user_id, user_id, request.blocked
    ))


@app.delete("/users/{user_id}")
def delete_user(user_id: str) -> Dict[str, str]:
    def operation() -> Dict[str, str]:
        if user_id not in api_system.users:
            raise KeyError(f"User '{user_id}' not found.")
        if any(loan.user_id == user_id and loan.return_status != "RETURNED"
               for loan in api_system.loans.values()):
            raise ValueError("Cannot delete a user with an active or pending loan.")
        if any(res.user_id == user_id and res.status in ("PENDING", "NOTIFIED")
               for res in api_system.reservations):
            raise ValueError("Cannot delete a user with an active reservation.")
        del api_system.users[user_id]
        return {"message": f"User '{user_id}' deleted."}

    return _run_write(operation)


@app.get("/books", response_model=List[Book])
def list_books() -> List[Book]:
    return list(api_system.catalog.values())


@app.get("/books/{isbn}", response_model=Book)
def get_book(isbn: str) -> Book:
    clean_isbn = isbn.replace("-", "").replace(" ", "").upper()
    book = api_system.catalog.get(clean_isbn)
    if book is None:
        raise HTTPException(status_code=404, detail=f"Book '{clean_isbn}' not found.")
    return book


@app.post("/books", response_model=Book, status_code=201)
def create_book(request: BookCreateRequest) -> Book:
    return _run_write(lambda: api_system.add_book(**request.model_dump()))


@app.patch("/books/{isbn}/copies", response_model=Book)
def update_book_copies(isbn: str, request: BookCopiesRequest) -> Book:
    return _run_write(lambda: api_system.update_book_copies(
        request.admin_user_id, isbn, request.additional_copies
    ))


@app.delete("/books/{isbn}")
def delete_book(isbn: str, admin_user_id: str = Query(...)) -> Dict[str, str]:
    def operation() -> Dict[str, str]:
        admin = api_system.users.get(admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError("Only administrators can delete catalog books.")
        clean_isbn = isbn.replace("-", "").replace(" ", "").upper()
        if clean_isbn not in api_system.catalog:
            raise KeyError(f"Book '{clean_isbn}' not found.")
        if any(loan.isbn == clean_isbn and loan.return_status != "RETURNED"
               for loan in api_system.loans.values()):
            raise ValueError("Cannot delete a book with an active or pending loan.")
        if any(res.isbn == clean_isbn and res.status in ("PENDING", "NOTIFIED")
               for res in api_system.reservations):
            raise ValueError("Cannot delete a book with an active reservation.")
        del api_system.catalog[clean_isbn]
        return {"message": f"Book '{clean_isbn}' deleted."}

    return _run_write(operation)


@app.get("/loans", response_model=List[LoanRecord])
def list_loans(user_id: Optional[str] = Query(default=None)) -> List[LoanRecord]:
    loans = list(api_system.loans.values())
    return [loan for loan in loans if user_id is None or loan.user_id == user_id]


@app.get("/loans/{loan_id}", response_model=LoanRecord)
def get_loan(loan_id: str) -> LoanRecord:
    loan = api_system.loans.get(loan_id)
    if loan is None:
        raise HTTPException(status_code=404, detail=f"Loan '{loan_id}' not found.")
    return loan


@app.post("/loans", response_model=LoanRecord, status_code=201)
def checkout_book(request: CheckoutRequest) -> LoanRecord:
    return _run_write(lambda: api_system.checkout_book(**request.model_dump()))


@app.post("/loans/{loan_id}/return", response_model=LoanRecord)
def request_return(loan_id: str) -> LoanRecord:
    return _run_write(lambda: api_system.request_return(loan_id))


@app.post("/loans/{loan_id}/approve", response_model=LoanRecord)
def approve_return(loan_id: str, request: ReturnApprovalRequest) -> LoanRecord:
    loan, _ = _run_write(lambda: api_system.approve_return_and_assess(
        request.admin_user_id, loan_id, request.damaged, request.damage_fee
    ))
    return loan


@app.get("/reservations", response_model=List[Reservation])
def list_reservations(user_id: Optional[str] = Query(default=None)) -> List[Reservation]:
    return [reservation for reservation in api_system.reservations
            if user_id is None or reservation.user_id == user_id]


@app.post("/reservations", response_model=Reservation, status_code=201)
def create_reservation(request: ReservationRequest) -> Reservation:
    return _run_write(lambda: api_system.place_reservation(**request.model_dump()))


@app.get("/reports/latest", response_model=LibraryReport)
def get_report() -> LibraryReport:
    return api_system.generate_system_report()


@app.post("/backup")
def backup_data(request: BackupRequest) -> Dict[str, str]:
    def operation() -> str:
        admin = api_system.users.get(request.admin_user_id)
        if not admin or admin.role != "admin":
            raise PermissionError("Only administrators can execute system state backup.")
        return api_system.backup_to_json(str(DATA_FILE))

    return {"path": _run_write(operation)}