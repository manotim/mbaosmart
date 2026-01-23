from django.urls import path
from . import views

app_name = 'hr'

urlpatterns = [
    # Employee URLs
    path('employees/', views.EmployeeListView.as_view(), name='employee_list'),
    path('employees/create/', views.EmployeeCreateView.as_view(), name='employee_create'),
    path('employees/<int:pk>/', views.EmployeeDetailView.as_view(), name='employee_detail'),
    path('employees/<int:pk>/edit/', views.EmployeeUpdateView.as_view(), name='employee_edit'),
    path('employees/<int:pk>/delete/', views.EmployeeDeleteView.as_view(), name='employee_delete'),
    
    # Work Log URLs
    path('work-logs/', views.WorkLogListView.as_view(), name='worklog_list'),
    path('work-logs/create/', views.WorkLogCreateView.as_view(), name='worklog_create'),
    path('work-logs/<int:pk>/edit/', views.WorkLogUpdateView.as_view(), name='worklog_edit'),
    
    # Attendance URLs
    path('attendance/', views.AttendanceListView.as_view(), name='attendance_list'),
    path('attendance/create/', views.AttendanceCreateView.as_view(), name='attendance_create'),
    path('attendance/<int:pk>/edit/', views.AttendanceUpdateView.as_view(), name='attendance_edit'),
    path('attendance/checkin/', views.attendance_checkin, name='attendance_checkin'),
    path('attendance/my/', views.MyAttendanceListView.as_view(), name='my_attendance'),
    
    # Payroll URLs
    path('payroll/', views.PayrollListView.as_view(), name='payroll_list'),
    path('payroll/create/', views.PayrollCreateView.as_view(), name='payroll_create'),
    path('payroll/<int:pk>/edit/', views.PayrollUpdateView.as_view(), name='payroll_edit'),
    
    # Leave Application URLs
    path('leaves/', views.LeaveApplicationListView.as_view(), name='leave_list'),
    path('leaves/create/', views.LeaveApplicationCreateView.as_view(), name='leave_create'),
    path('leaves/<int:pk>/edit/', views.LeaveApplicationUpdateView.as_view(), name='leave_edit'),
    
    # Task Dashboard URLs (For Fundis)
    path('task-dashboard/', views.TaskDashboardView.as_view(), name='task_dashboard'),
    path('tasks/<int:task_id>/complete/', views.mark_task_complete, name='mark_task_complete'),
    path('tasks/<int:task_id>/verify/', views.verify_task, name='verify_task'),

    path('tasks/<int:pk>/start/', views.start_task, name='task_start'),
    path('tasks/<int:pk>/complete/', views.complete_task, name='task_complete'),
    path('tasks/<int:pk>/update/', views.update_task_progress, name='task_update'),

    path('leaves/<int:pk>/details/', views.LeaveDetailView.as_view(), name='leave_details'),
    path('leaves/process/', views.leave_process, name='leave_process'),
    path('work-logs/<int:pk>/mark-paid/', views.worklog_mark_paid, name='worklog_mark_paid'),
    path('payroll/<int:pk>/mark-paid/', views.payroll_mark_paid, name='payroll_mark_paid'),
    
    # API URLs
    path('api/employee/<int:employee_id>/tasks/', views.get_employee_tasks, name='employee_tasks_api'),
    path('api/dashboard-stats/', views.dashboard_stats, name='dashboard_stats_api'),
]