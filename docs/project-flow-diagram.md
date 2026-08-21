# MehndiVerse Project Flow Diagram

This is the quickest way to understand what MehndiVerse does and how its parts
work together. It reflects the implemented platform flow: customers discover
designs and book artists; artists manage their services and requests; admins
keep the marketplace safe and operational.

Open this file in GitHub, VS Code with a Mermaid preview extension, or any
Mermaid-compatible Markdown viewer to see the rendered diagram.

```mermaid
flowchart TB
    Start([Visitor opens MehndiVerse]) --> Access{Has an account?}
    Access -->|No| Browse[Browse designs, search, and view artists]
    Access -->|Yes| SignIn[Sign in with Supabase Auth]
    Browse --> Choice{What does the user want to do?}
    SignIn --> Choice

    subgraph Customer[Customer flow]
        direction TB
        Discover[Discover a design or artist]
        Save[Like, save, or add a design to a collection]
        Profile[Open artist profile, portfolio, services, and availability]
        Draft[Create booking draft and add details or inspiration images]
        Submit[Submit booking request]
        Quote[Review artist quotation and message the artist]
        Accept{Accept quotation?}
        Deposit{Is a deposit required?}
        Pay[Pay securely through Razorpay]
        Confirm[Booking confirmed]
        Service[Artist delivers the service]
        Review[Leave a review]

        Discover --> Save
        Discover --> Profile
        Profile --> Draft --> Submit --> Quote --> Accept
        Accept -->|No| Discover
        Accept -->|Yes| Deposit
        Deposit -->|No| Confirm
        Deposit -->|Yes| Pay --> Confirm
        Confirm --> Service --> Review
    end

    subgraph Artist[Artist flow]
        direction TB
        ArtistSetup[Create artist profile]
        Verification[Upload verification documents]
        AdminCheck{Admin approves artist?}
        Improve[Update profile or documents]
        Marketplace[Publish portfolio, services, and availability]
        Inbox[Receive booking request]
        SendQuote[Review request, message customer, and send quotation]
        Manage[Manage confirmed booking and mark service complete]

        ArtistSetup --> Verification --> AdminCheck
        AdminCheck -->|Needs changes or rejected| Improve --> Verification
        AdminCheck -->|Approved| Marketplace --> Inbox --> SendQuote --> Manage
    end

    subgraph Admin[Admin flow]
        direction TB
        Dashboard[Admin dashboard]
        Verify[Review artist verification]
        Moderate[Moderate designs, comments, reviews, and reports]
        Operate[Oversee users, bookings, payments, refunds, categories, and analytics]

        Dashboard --> Verify
        Dashboard --> Moderate
        Dashboard --> Operate
    end

    Choice -->|Explore or book| Discover
    Choice -->|Offer mehndi services| ArtistSetup
    Choice -->|Staff account| Dashboard
    Submit --> Inbox
    SendQuote --> Quote
    Verify --> AdminCheck
    Moderate -.->|keeps marketplace safe| Discover
    Operate -.->|support and intervention| Confirm

    subgraph Platform[Shared platform services]
        direction LR
        Clients[Flutter mobile app, customer web app, and admin dashboard]
        API[FastAPI API<br/>Business rules and authorization]
        Auth[Supabase Auth]
        Data[(PostgreSQL with RLS)]
        Files[Supabase Storage<br/>Images, documents, attachments]
        Queue[(Redis<br/>Cache and background jobs)]
        Workers[Background workers<br/>Notifications and media processing]
        Payments[Razorpay<br/>Payment orders and webhooks]
        Notify[Push and email providers]

        Clients -->|authenticated API requests| API
        Clients -.->|identity and session| Auth
        API -.->|validates token| Auth
        API --> Data
        API --> Files
        API --> Queue
        API --> Payments
        Queue --> Workers
        Workers --> Data
        Workers --> Files
        Workers --> Notify
    end

    Customer -.-> Clients
    Artist -.-> Clients
    Admin -.-> Clients
    Pay -.-> Payments

    classDef customer fill:#fff2cc,stroke:#b8860b,color:#332600;
    classDef artist fill:#d9ead3,stroke:#38761d,color:#173b0e;
    classDef admin fill:#d9eaf7,stroke:#1155cc,color:#0b2e61;
    classDef platform fill:#eadcf8,stroke:#674ea7,color:#2c174c;
    class Discover,Save,Profile,Draft,Submit,Quote,Accept,Deposit,Pay,Confirm,Service,Review customer;
    class ArtistSetup,Verification,AdminCheck,Improve,Marketplace,Inbox,SendQuote,Manage artist;
    class Dashboard,Verify,Moderate,Operate admin;
    class Clients,API,Auth,Data,Files,Queue,Workers,Payments,Notify platform;
```

## How to read it

- Solid arrows are normal user or system actions.
- Dashed arrows show a supporting connection, rather than the main journey.
- Yellow is the customer journey, green is the artist journey, blue is the
  admin journey, and purple is shared technical infrastructure.
- A booking connects the customer and artist journeys. Payment confirmation is
  controlled by the backend using Razorpay webhooks, rather than trusting a
  browser or mobile-app success message.

## Important booking outcomes

The main happy path above is intentionally simple. A booking can also be
cancelled or rejected, rescheduled, disputed, or (after completion) enter a
refund process. For the complete status-by-status state machine, see
[booking-lifecycle.md](booking-lifecycle.md).

## Related documentation

- [System architecture](system-architecture.md)
- [Product requirements](product-requirements.md)
- [Roles and permissions](user-roles-and-permissions.md)
- [Payment flow](payments.md)
