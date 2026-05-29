import csv
import sys
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db.models import Sum, Avg, Count
from features.models import ErrorAnalysisLog
from features.patent_metrics import generate_patent_summary

class Command(BaseCommand):
    help = 'Calculates and displays the quantitative patent metrics for token optimization and API cost reduction.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--export-csv',
            action='store_true',
            help='Export the raw metrics to patent_metrics_export.csv',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Calculating Patent Metrics..."))
        
        total_errors = ErrorAnalysisLog.objects.count()
        if total_errors == 0:
            self.stdout.write(self.style.WARNING("No error analysis records found in the database."))
            return

        heuristic_resolved = ErrorAnalysisLog.objects.filter(was_sent_to_llm=False).count()
        llm_invocations = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True).count()
        
        heuristic_rate = (heuristic_resolved / total_errors) * 100 if total_errors > 0 else 0
        llm_reduction = heuristic_rate # Since any resolved by heuristic is an LLM invocation saved
        
        total_prompt_tokens = ErrorAnalysisLog.objects.aggregate(total=Sum('prompt_tokens'))['total'] or 0
        total_completion_tokens = ErrorAnalysisLog.objects.aggregate(total=Sum('completion_tokens'))['total'] or 0
        actual_tokens_used = total_prompt_tokens + total_completion_tokens
        
        # Calculate baselines
        llm_logs = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True)
        if llm_logs.exists():
            avg_prompt = llm_logs.aggregate(avg=Avg('prompt_tokens'))['avg'] or 0
            avg_completion = llm_logs.aggregate(avg=Avg('completion_tokens'))['avg'] or 0
            avg_cost = llm_logs.aggregate(avg=Avg('api_cost_usd'))['avg'] or Decimal('0.0')
        else:
            avg_prompt = 150
            avg_completion = 50
            avg_cost = Decimal('0.00002625') # default cost
            
        baseline_tokens = total_errors * (avg_prompt + avg_completion)
        token_savings_pct = ((baseline_tokens - actual_tokens_used) / baseline_tokens * 100) if baseline_tokens > 0 else 0
        
        actual_api_cost = ErrorAnalysisLog.objects.aggregate(total=Sum('api_cost_usd'))['total'] or Decimal('0.0')
        baseline_api_cost = Decimal(str(total_errors)) * avg_cost
        api_cost_reduction_pct = ((baseline_api_cost - actual_api_cost) / baseline_api_cost * 100) if baseline_api_cost > 0 else Decimal('0.0')

        heuristic_latency = ErrorAnalysisLog.objects.filter(was_sent_to_llm=False).aggregate(avg=Avg('total_latency_ms'))['avg'] or 0
        llm_latency = ErrorAnalysisLog.objects.filter(was_sent_to_llm=True).aggregate(avg=Avg('total_latency_ms'))['avg'] or 0
        avg_overall = ErrorAnalysisLog.objects.aggregate(avg=Avg('total_latency_ms'))['avg'] or 0
        
        response_time_reduction = ((llm_latency - heuristic_latency) / llm_latency * 100) if llm_latency > 0 else 0

        # Print Output
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(" PATENT METRICS REPORT "))
        self.stdout.write("="*50)
        self.stdout.write(f"Total incorrect responses analyzed: {total_errors}")
        self.stdout.write(f"Resolved by heuristic gate: {heuristic_resolved}")
        self.stdout.write(f"Sent to LLM: {llm_invocations}")
        self.stdout.write(f"Heuristic Resolution Rate: {heuristic_rate:.1f}%")
        self.stdout.write(f"LLM Invocation Reduction: {llm_reduction:.1f}%")
        
        self.stdout.write("-" * 50)
        self.stdout.write(f"Total prompt tokens: {total_prompt_tokens}")
        self.stdout.write(f"Total completion tokens: {total_completion_tokens}")
        self.stdout.write(f"Total tokens used: {actual_tokens_used}")
        self.stdout.write(f"Baseline tokens (if all sent to LLM): {int(baseline_tokens)}")
        self.stdout.write(self.style.WARNING(f"Token Savings: {token_savings_pct:.1f}%"))
        
        self.stdout.write("-" * 50)
        self.stdout.write(f"Total API cost: ${actual_api_cost:.6f}")
        self.stdout.write(f"Baseline API cost: ${baseline_api_cost:.6f}")
        self.stdout.write(self.style.WARNING(f"API Cost Reduction: {api_cost_reduction_pct:.1f}%"))
        
        self.stdout.write("-" * 50)
        self.stdout.write(f"Average heuristic processing time: {heuristic_latency:.0f} ms")
        self.stdout.write(f"Average LLM processing time: {llm_latency:.0f} ms")
        self.stdout.write(f"Average overall processing time: {avg_overall:.0f} ms")
        self.stdout.write(self.style.WARNING(f"Average Response Time Reduction: {response_time_reduction:.1f}%"))
        self.stdout.write("=" * 50)
        
        self.stdout.write("\n" + self.style.SUCCESS(" PATENT SUMMARY PARAGRAPH "))
        self.stdout.write("-" * 50)
        self.stdout.write(generate_patent_summary())
        self.stdout.write("-" * 50 + "\n")

        if options['export_csv']:
            self.export_to_csv()

    def export_to_csv(self):
        filename = 'patent_metrics_export.csv'
        logs = ErrorAnalysisLog.objects.all()
        try:
            with open(filename, mode='w', newline='') as file:
                writer = csv.writer(file)
                writer.writerow([
                    'ID', 'User', 'Question_ID', 'Was_Sent_To_LLM', 
                    'Heuristic_Category', 'LLM_Category', 
                    'Prompt_Tokens', 'Completion_Tokens', 'API_Cost_USD', 
                    'Latency_ms', 'Created_At'
                ])
                for log in logs:
                    writer.writerow([
                        log.id,
                        log.user.username if log.user else 'Anonymous',
                        log.question_id,
                        log.was_sent_to_llm,
                        log.heuristic_category,
                        log.llm_category,
                        log.prompt_tokens,
                        log.completion_tokens,
                        log.api_cost_usd,
                        log.total_latency_ms,
                        log.created_at
                    ])
            self.stdout.write(self.style.SUCCESS(f"Successfully exported data to {filename}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to export CSV: {e}"))
