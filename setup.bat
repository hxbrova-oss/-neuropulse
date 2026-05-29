@echo off
chcp 65001 >nul
echo ============================================
echo  نظام الربح المؤتمت - الإعداد الأولي
echo ============================================
echo.

echo [1/4] إنشاء بيئة افتراضية...
python -m venv venv
call venv\Scripts\activate.bat

echo [2/4] تثبيت المكتبات...
pip install -r requirements.txt

echo [3/4] التحقق من الملفات...
if not exist .env (
    echo.
    echo ⚠️  ملف .env غير موجود!
    echo    انسخ env.example إلى .env وأضف القيم الحقيقية
    echo.
    copy env.example .env
    echo    تم إنشاء .env من env.example - عدّل القيم الآن
) else (
    echo ✅ ملف .env موجود
)

echo.
echo [4/4] تم الإعداد بنجاح!
echo.
echo الخطوات التالية:
echo 1. عدّل ملف .env بالقيم الحقيقية
echo 2. نفذ SQL في Supabase من supabase_schema.sql
echo 3. استورد n8n_workflow.json في n8n
echo 4. شغّل: python discovery_engine.py
echo.
pause
