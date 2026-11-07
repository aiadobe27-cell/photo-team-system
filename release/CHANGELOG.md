# PHOTO TEAM SYSTEM - Changelog

## V80 — Sapphire White & Blue Edition (الواجهة البيضاء والزرقاء الجديدة)
- تصميم نظام بصري جديد بالكامل باللونين **الأبيض النقي والأزرق الملكي/السماوي (Sapphire White & Blue)** مع الحفاظ الكامل (100%) على نفس المنطق البرمجي والحسابات وقاعدة البيانات.
- إعادة تصميم القائمة الجانبية (Sidebar) والشريط العلوي (Top Header) مع تفعيل الساعة الحية والتاريخ ومؤشر اتصال قاعدة البيانات المباشر.
- إعادة تصميم شاشة تسجيل الدخول (`login.html` + `login.css`) بهوية بصرية زرقاء وبيضاء عصرية.
- توحيد تصميم الكروت، مؤشرات الأداء (KPIs)، الجداول ذات الرؤوس الزرقاء الفاتحة الثابتة، والتبويبات، والنوافذ المنبثقة في جميع الشاشات الـ 12.
- إصلاح شاشة غرفة العمليات (`control_room.html` / `control_room.js`) بإزالة النصوص الزائدة وتفعيل أزرار وضع الشاشة (TV Kiosk Mode)، التنبيهات الصوتية، ومؤشر الساعة الذهبية.
- ضبط الألوان المالية (الدولار، اليورو، الجنيه المصري) وملخصات الحسابات في شاشة المبيعات اليومية والعمولات والمرتبات لتظهر بوضوح تام وتباين عالٍ على الخلفية البيضاء والزرقاء.


## V73 — Per-page structure & layout cleanup
- كل صفحة ليها 3 ملفات: templates/<page>.html + static/css/pages/<page>.css + static/js/pages/<page>.js
- ستايل كل صفحة متغلف بـ :where(body.page-<page>) فمش ممكن يأثر على صفحة تانية.
- المشترك في static/css/core و static/js/core.
- حذف: ملفات v48–v71، modules/، static/modules/، ملفات CSS غير متحملة (light-theme.css, core.css…)، docs فاضية، صور مش مستخدمة.
- CSS: حذف 105 قاعدة لكلاسات غير موجودة + 312 خاصية ملغية + 41 قاعدة مكررة + @import غلط.
- الأيقونات PNG اتصغرت من ~4.7MB لـ ~0.3MB (نفس الأسماء).
- القائمة الجانبية: الأسماء ما بقتش بتتكسر، واللوجو وعناوين الأقسام وزرار الخروج اتظبطوا.
- كل الـ grids بقت minmax(0, 1fr) — الجداول العريضة بتعمل scroll جوه الكارت بدل ما تخرج برا الصفحة.
- الرئيسية: كارت الترحيب ما بقاش متزنق.
- login.js: classList بدل className (علشان ما يمسحش كلاس الصفحة).


## V72 — Context Menu & Theme Fix
- قائمة الكليك اليمين: محرك جديد (v72_context_menu_fix.js) بدل v45؛ الأزرار بتنفذ الإجراءات الحقيقية.
- قائمة الحجوزات بالكليك اليمين: Checkout، التفاصيل، تعديل، استنساخ، واتساب، كارت الموعد، حذف.
- باقي الصفحات: القائمة بتعرض أزرار الإجراءات الموجودة في الصف تلقائياً.
- الكليك اليمين على الحقول/النص المتحدد/عناوين الجداول رجع لقائمة المتصفح (نسخ/لصق).
- إصلاح Enter اللي كان بيضغط الزر مرتين (حفظ/حذف مكرر).
- إصلاح تعارض الثيم: نظام واحد بدل نظامين (app.js + base.html).
- جدول الحجوزات: العواميد رجعت متطابقة مع العناوين (19 عمود) + كبسولة المصور.
- حذف تعريف statusBadge المكرر في reservations.js.
- freeze_support لنسخة الـ EXE + إضافة flaskwebgui لـ requirements.
- تصحيح أسماء متغيرات البيئة في config/production.env.example.
- PhotoTeam.spec و build_exe.bat لإعادة بناء الـ EXE.



## V70 Gold Release

Finalized:
- UI system improvements
- Module organization
- Production preparation
- Verification checklist
- Deployment preparation

## Main Modules
- Dashboard
- Bookings
- Finance
- Inventory
- Reports
- Team
- Settings
