import { BookingCalendarView } from "./booking-calendar-view";

export default function ArtistBookingCalendarPage() {
  return (
    <div className="mx-auto max-w-4xl px-4 py-12 sm:px-6">
      <h1 className="font-display text-3xl font-semibold text-text-primary">Booking calendar</h1>
      <p className="mt-1 text-text-secondary">
        Confirmed and in-progress bookings that occupy your calendar.
      </p>
      <div className="mt-6">
        <BookingCalendarView />
      </div>
    </div>
  );
}
