# 🌍 WanderList – Travel Bucket List and Planner

**WanderList** is a Python-based desktop application developed using Tkinter that helps users organize their dream travel destinations and plan their trips efficiently.

The application provides a simple and interactive interface where users can maintain a travel bucket list, create itineraries, estimate travel expenses, prepare packing checklists and record their travel memories.

---

## ✨ Features

### 1. Dashboard
- View the total number of saved destinations.
- Track visited destinations.
- Monitor upcoming trips.
- View the total estimated travel budget.
- Access recently added destinations.

### 2. My Bucket List
- Add, edit and delete travel destinations.
- Categorize destinations by type.
- Set travel priorities (High, Medium, Low).
- Track destination status (Wishlist, Planned, Visited).
- Search and filter saved destinations.

### 3. Trip Planner & Itinerary
- Create travel plans using saved destinations.
- Set trip start and end dates.
- Add activities to individual trips.
- Organize activities by date and time.
- Edit and delete itinerary activities.

### 4. Travel Budget Planner
- Estimate transportation expenses.
- Calculate accommodation and food costs.
- Track activities and miscellaneous expenses.
- Set a total estimated budget.
- Automatically calculate total expenses and remaining budget.
- Identify trips that exceed the planned budget.

### 5. Trip Checklist & Travel Memories
- Create personalized packing checklists.
- Use predefined packing suggestions.
- Mark checklist items as completed.
- Track checklist completion progress.
- Mark destinations as visited.
- Save travel dates and personal memories.

---

## 🛠️ Technologies Used

- **Python 3** – Core programming language.
- **Tkinter** – Graphical User Interface development.
- **Tkinter ttk** – Styled GUI components.
- **JSON** – Local data storage.
- **Datetime** – Date and time validation.

---

## 📁 Project Structure

```text
Tkinter-Project/
│
├── wanderlist.py
├── WanderList_Project_Presentation_with_Architecture.pptx
├── README.md
└── .gitignore
```

The application automatically generates `wanderlist_data.json` when it saves data for the first time.

---

## ⚙️ Installation and Setup

### Prerequisites
- Python 3.10 or newer.
- Tkinter support.

### Steps to Run

1. Clone the repository:

```bash
git clone https://github.com/sritamadutta5/Tkinter-Project-.git
```

2. Navigate to the project directory:

```bash
cd Tkinter-Project-
```

3. Run the application:

```bash
python wanderlist.py
```

No additional Python packages are required.

---

## 💾 Data Storage

WanderList uses JSON-based local storage to preserve user information.

The application automatically creates and updates `wanderlist_data.json` to store:
- Travel destinations
- Trip details and itineraries
- Budget information
- Checklist items
- Travel memories

Data remains available when the application is closed and reopened.

---

## 🎨 Interface Design

The application uses a clean desktop interface with a forest green and warm cream colour palette.

It includes a sidebar navigation system, organized data tables, input forms and dashboard summary cards for a consistent user experience.

---

## 🎓 Project Information

**Project:** WanderList – Travel Bucket List and Planner

**Domain:** Desktop Application Development

**Framework:** Python Tkinter

**Project Type:** Academic Internal Assignment

---

*Plan your journeys, organize your adventures and keep your travel dreams alive with WanderList! ✈️*
