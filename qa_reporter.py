import json
import os
from datetime import datetime, timedelta
from typing import Dict, List
import csv

class QAGateReporter:
    """
    Automated QA Gate Weekly Report System for Sava Health
    Tracks QA gates completed, time spent, blockers, and tickets
    """
    
    def __init__(self, data_file='qa_gate_data.json'):
        self.data_file = data_file
        self.data = self.load_data()
        
        # QA Gate types from your process
        self.gate_types = [
            'Dispensing (LN-Q)',
            'Screen Printing (LN-P)',
            'Outer Layer (LN-R)',
            'Final Inspection (LN-C)'
        ]
        
        # Common blockers you face
        self.common_blockers = [
            'SME review delay',
            'Imaging files not available on SharePoint',
            'QCI deviation - awaiting approval',
            'Steel Mountain upload issues',
            'Lot report generation delay',
            'Multiple lots requiring individual uploads',
            'Unclear failure criteria',
            'SME added/removed sensors - rework needed'
        ]
        
        # Ticket categories
        self.ticket_categories = [
            'Imaging System',
            'Steel Mountain',
            'QCI Clarification',
            'Process Improvement',
            'Equipment Issue',
            'Other'
        ]
    
    def load_data(self) -> Dict:
        """Load existing data or create new structure"""
        if os.path.exists(self.data_file):
            with open(self.data_file, 'r') as f:
                return json.load(f)
        return {'entries': [], 'tickets': []}
    
    def save_data(self):
        """Save data to JSON file"""
        with open(self.data_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    def log_qa_gate(self):
        """Interactive logging of a QA gate completion"""
        print("\n=== LOG QA GATE COMPLETION ===\n")
        
        # Date
        date_input = input("Date (press Enter for today, or YYYY-MM-DD): ").strip()
        if not date_input:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = date_input
        
        # Gate type
        print("\nQA Gate Type:")
        for i, gate in enumerate(self.gate_types, 1):
            print(f"{i}. {gate}")
        gate_choice = int(input("Select gate type (1-4): "))
        gate_type = self.gate_types[gate_choice - 1]
        
        # Lot number
        lot_number = input("\nLot Number (e.g., LN-Q12345): ").strip()
        
        # Time spent
        time_spent = float(input("Time spent (hours): "))
        
        # Number of sensors
        total_sensors = int(input("Total sensors reviewed: "))
        accepted = int(input("Sensors accepted: "))
        rejected = total_sensors - accepted
        
        # Blockers
        print("\nBlockers encountered (if any):")
        print("0. None")
        for i, blocker in enumerate(self.common_blockers, 1):
            print(f"{i}. {blocker}")
        print(f"{len(self.common_blockers) + 1}. Other (specify)")
        
        blockers = []
        while True:
            choice = input("Select blocker (0 when done): ").strip()
            if choice == '0':
                break
            choice_num = int(choice)
            if choice_num <= len(self.common_blockers):
                blockers.append(self.common_blockers[choice_num - 1])
            else:
                custom = input("Specify blocker: ")
                blockers.append(custom)
        
        # SME review cycles
        sme_cycles = int(input("\nNumber of SME review cycles (1 if no rework): "))
        
        # Notes
        notes = input("Additional notes (optional): ").strip()
        
        # Create entry
        entry = {
            'date': date,
            'gate_type': gate_type,
            'lot_number': lot_number,
            'time_spent_hours': time_spent,
            'total_sensors': total_sensors,
            'accepted': accepted,
            'rejected': rejected,
            'yield_percentage': round((accepted / total_sensors) * 100, 2),
            'blockers': blockers,
            'sme_review_cycles': sme_cycles,
            'notes': notes
        }
        
        self.data['entries'].append(entry)
        self.save_data()
        
        print("\n✓ QA Gate logged successfully!")
    
    def log_ticket(self):
        """Log a ticket submitted"""
        print("\n=== LOG TICKET SUBMISSION ===\n")
        
        date_input = input("Date (press Enter for today, or YYYY-MM-DD): ").strip()
        if not date_input:
            date = datetime.now().strftime('%Y-%m-%d')
        else:
            date = date_input
        
        ticket_id = input("Ticket ID (e.g., JIRA-1234): ").strip()
        
        print("\nTicket Category:")
        for i, category in enumerate(self.ticket_categories, 1):
            print(f"{i}. {category}")
        cat_choice = int(input("Select category (1-6): "))
        category = self.ticket_categories[cat_choice - 1]
        
        assigned_to = input("Assigned to (team/person): ").strip()
        description = input("Brief description: ").strip()
        
        status = input("Status (Open/In Progress/Resolved): ").strip() or "Open"
        
        ticket = {
            'date': date,
            'ticket_id': ticket_id,
            'category': category,
            'assigned_to': assigned_to,
            'description': description,
            'status': status
        }
        
        self.data['tickets'].append(ticket)
        self.save_data()
        
        print("\n✓ Ticket logged successfully!")
    
    def generate_weekly_report(self):
        """Generate comprehensive weekly report"""
        print("\n=== GENERATE WEEKLY REPORT ===\n")
        
        # Get date range
        end_date_input = input("End date (press Enter for today, or YYYY-MM-DD): ").strip()
        if not end_date_input:
            end_date = datetime.now()
        else:
            end_date = datetime.strptime(end_date_input, '%Y-%m-%d')
        
        start_date = end_date - timedelta(days=7)
        
        # Filter entries for this week
        week_entries = [
            e for e in self.data['entries']
            if start_date.strftime('%Y-%m-%d') <= e['date'] <= end_date.strftime('%Y-%m-%d')
        ]
        
        week_tickets = [
            t for t in self.data['tickets']
            if start_date.strftime('%Y-%m-%d') <= t['date'] <= end_date.strftime('%Y-%m-%d')
        ]
        
        # Generate report
        report = self._format_report(week_entries, week_tickets, start_date, end_date)
        
        # Save report
        filename = f"QA_Weekly_Report_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}.txt"
        with open(filename, 'w') as f:
            f.write(report)
        
        print(report)
        print(f"\n✓ Report saved to {filename}")
    
    def _format_report(self, entries: List, tickets: List, start: datetime, end: datetime) -> str:
        """Format the weekly report"""
        report_lines = []
        report_lines.append("=" * 70)
        report_lines.append("SAVA HEALTH - QA GATE WEEKLY REPORT")
        report_lines.append(f"Report Period: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        report_lines.append("=" * 70)
        
        # Summary Statistics
        report_lines.append("\n📊 SUMMARY STATISTICS")
        report_lines.append("-" * 70)
        
        total_gates = len(entries)
        total_time = sum(e['time_spent_hours'] for e in entries)
        total_sensors = sum(e['total_sensors'] for e in entries)
        total_accepted = sum(e['accepted'] for e in entries)
        total_rejected = sum(e['rejected'] for e in entries)
        
        avg_yield = (total_accepted / total_sensors * 100) if total_sensors > 0 else 0
        avg_time_per_gate = total_time / total_gates if total_gates > 0 else 0
        
        report_lines.append(f"Total QA Gates Completed: {total_gates}")
        report_lines.append(f"Total Time Spent: {total_time:.2f} hours")
        report_lines.append(f"Average Time per Gate: {avg_time_per_gate:.2f} hours")
        report_lines.append(f"Total Sensors Reviewed: {total_sensors}")
        report_lines.append(f"  ✓ Accepted: {total_accepted}")
        report_lines.append(f"  ✗ Rejected: {total_rejected}")
        report_lines.append(f"Overall Yield: {avg_yield:.2f}%")
        
        # Breakdown by gate type
        report_lines.append("\n📋 QA GATES BY TYPE")
        report_lines.append("-" * 70)
        
        gate_breakdown = {}
        for entry in entries:
            gate_type = entry['gate_type']
            if gate_type not in gate_breakdown:
                gate_breakdown[gate_type] = {
                    'count': 0,
                    'time': 0,
                    'sensors': 0,
                    'accepted': 0
                }
            gate_breakdown[gate_type]['count'] += 1
            gate_breakdown[gate_type]['time'] += entry['time_spent_hours']
            gate_breakdown[gate_type]['sensors'] += entry['total_sensors']
            gate_breakdown[gate_type]['accepted'] += entry['accepted']
        
        for gate_type, stats in gate_breakdown.items():
            yield_pct = (stats['accepted'] / stats['sensors'] * 100) if stats['sensors'] > 0 else 0
            report_lines.append(f"\n{gate_type}:")
            report_lines.append(f"  Gates: {stats['count']} | Time: {stats['time']:.2f}h | Yield: {yield_pct:.1f}%")
        
        # Blockers encountered
        report_lines.append("\n🚧 BLOCKERS & CHALLENGES")
        report_lines.append("-" * 70)
        
        all_blockers = []
        sme_rework_count = 0
        for entry in entries:
            all_blockers.extend(entry['blockers'])
            if entry['sme_review_cycles'] > 1:
                sme_rework_count += 1
        
        if all_blockers:
            blocker_counts = {}
            for blocker in all_blockers:
                blocker_counts[blocker] = blocker_counts.get(blocker, 0) + 1
            
            sorted_blockers = sorted(blocker_counts.items(), key=lambda x: x[1], reverse=True)
            for blocker, count in sorted_blockers:
                report_lines.append(f"  • {blocker}: {count} occurrence(s)")
        else:
            report_lines.append("  No blockers reported this week! 🎉")
        
        report_lines.append(f"\nQA Gates requiring SME rework: {sme_rework_count}/{total_gates}")
        
        # Tickets
        report_lines.append("\n🎫 TICKETS SUBMITTED")
        report_lines.append("-" * 70)
        
        if tickets:
            report_lines.append(f"Total tickets submitted: {len(tickets)}\n")
            
            ticket_by_category = {}
            for ticket in tickets:
                cat = ticket['category']
                if cat not in ticket_by_category:
                    ticket_by_category[cat] = []
                ticket_by_category[cat].append(ticket)
            
            for category, cat_tickets in ticket_by_category.items():
                report_lines.append(f"\n{category} ({len(cat_tickets)}):")
                for ticket in cat_tickets:
                    report_lines.append(f"  • {ticket['ticket_id']} - {ticket['description']}")
                    report_lines.append(f"    Assigned to: {ticket['assigned_to']} | Status: {ticket['status']}")
        else:
            report_lines.append("  No tickets submitted this week")
        
        # Detailed gate log
        report_lines.append("\n📝 DETAILED QA GATE LOG")
        report_lines.append("-" * 70)
        
        for entry in sorted(entries, key=lambda x: x['date']):
            report_lines.append(f"\n{entry['date']} - {entry['lot_number']} ({entry['gate_type']})")
            report_lines.append(f"  Time: {entry['time_spent_hours']}h | "
                              f"Sensors: {entry['accepted']}/{entry['total_sensors']} accepted "
                              f"({entry['yield_percentage']}% yield)")
            if entry['blockers']:
                report_lines.append(f"  Blockers: {', '.join(entry['blockers'])}")
            if entry['notes']:
                report_lines.append(f"  Notes: {entry['notes']}")
        
        # Recommendations
        report_lines.append("\n💡 RECOMMENDATIONS & ACTION ITEMS")
        report_lines.append("-" * 70)
        
        # Auto-generate recommendations based on data
        if avg_time_per_gate > 3:
            report_lines.append("  • Average time per gate exceeds 3 hours - consider process optimization")
        
        if sme_rework_count > total_gates * 0.3:
            report_lines.append("  • High SME rework rate - standardize QCI criteria and failure modes")
        
        if 'QCI deviation - awaiting approval' in [b for e in entries for b in e['blockers']]:
            report_lines.append("  • QCI deviations detected - implement deviation tracking with signed forms")
        
        if 'Unclear failure criteria' in [b for e in entries for b in e['blockers']]:
            report_lines.append("  • Create gold standard images for each failure mode")
        
        report_lines.append("\n" + "=" * 70)
        
        return "\n".join(report_lines)
    
    def view_data(self):
        """View all logged data"""
        print("\n=== VIEW DATA ===\n")
        print(f"Total QA Gates logged: {len(self.data['entries'])}")
        print(f"Total Tickets logged: {len(self.data['tickets'])}")
        
        if self.data['entries']:
            print("\nRecent QA Gates:")
            for entry in self.data['entries'][-5:]:
                print(f"  {entry['date']} - {entry['lot_number']} - {entry['time_spent_hours']}h")
    
    def run(self):
        """Main menu loop"""
        while True:
            print("\n" + "=" * 50)
            print("SAVA HEALTH QA GATE WEEKLY REPORTER")
            print("=" * 50)
            print("\n1. Log QA Gate Completion")
            print("2. Log Ticket Submission")
            print("3. Generate Weekly Report")
            print("4. View All Data")
            print("5. Exit")
            
            choice = input("\nSelect option (1-5): ").strip()
            
            if choice == '1':
                self.log_qa_gate()
            elif choice == '2':
                self.log_ticket()
            elif choice == '3':
                self.generate_weekly_report()
            elif choice == '4':
                self.view_data()
            elif choice == '5':
                print("\nGoodbye! Keep up the great QA work! 💪")
                break
            else:
                print("\nInvalid choice. Please try again.")

if __name__ == "__main__":
    reporter = QAGateReporter()
    reporter.run()
    