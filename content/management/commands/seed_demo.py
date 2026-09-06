import os
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from content.models import (
    AboutPage,
    CurriculumDocument,
    CurriculumGrade,
    Event,
    Facility,
    GalleryAlbum,
    GalleryImage,
    HomeContent,
    Leader,
    NewsPost,
    SiteSettings,
    Subject,
    SubjectCategory,
    WhyChooseItem,
    NewsCategory,
    GalleryCategory,
)
from admissions.models import AdmissionFee, PaymentMethod

IMG = {
    "hero": "https://images.unsplash.com/photo-1609599006353-e629aaabfeae?auto=format&fit=crop&w=1600&q=80",
    "quran": "https://images.unsplash.com/photo-1584551246679-0daf3d275d0f?auto=format&fit=crop&w=1200&q=80",
    "classroom": "https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=1200&q=80",
    "campus": "https://images.unsplash.com/photo-1564769625905-50e93615e769?auto=format&fit=crop&w=1200&q=80",
    "kids": "https://images.unsplash.com/photo-1509062522246-3755977927d7?auto=format&fit=crop&w=1200&q=80",
    "library": "https://images.unsplash.com/photo-1481627834876-b7833e8f5570?auto=format&fit=crop&w=1200&q=80",
    "sports": "https://images.unsplash.com/photo-1517649763962-0c623066027b?auto=format&fit=crop&w=1200&q=80",
    "culture": "https://images.unsplash.com/photo-1533174072545-7a4b6ad7a6c3?auto=format&fit=crop&w=1200&q=80",
    "principal": "https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=600&q=80",
    "leader2": "https://images.unsplash.com/photo-1580489944761-15a19d654956?auto=format&fit=crop&w=600&q=80",
    "leader3": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=600&q=80",
}


class Command(BaseCommand):
    help = "Load bilingual demo content for the IGQS public website."

    def handle(self, *args, **options):
        self._settings()
        self._home()
        self._about()
        self._curriculum()
        self._payments()
        self._events()
        self._news()
        self._gallery()
        self._staff()
        self.stdout.write(self.style.SUCCESS("Demo content seeded."))

    def _staff(self):
        User = get_user_model()
        username = os.getenv("STAFF_USERNAME", "igqs")
        password = os.getenv("STAFF_PASSWORD", "igqs-admin-2026")
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                "is_staff": True,
                "is_superuser": True,
                "email": "admissions@igqs.edu.bd",
                "first_name": "IGQS",
                "last_name": "Admin",
            },
        )
        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()
        state = "created" if created else "updated"
        self.stdout.write(self.style.SUCCESS(f"Staff user {username} {state}."))

    def _settings(self):
        SiteSettings.objects.update_or_create(
            pk=1,
            defaults={
                "school_name_en": "Ideal Global Qur'anic School",
                "school_name_bn": "আদর্শ গ্লোবাল কুরআনিক স্কুল",
                "tagline_en": "Nurturing hearts with the Qur'an, minds with knowledge.",
                "tagline_bn": "কুরআন দিয়ে হৃদয় গড়ি, জ্ঞান দিয়ে মন গড়ি।",
                "address_en": "House 18, Road 7, Uttara, Dhaka 1230, Bangladesh",
                "address_bn": "বাড়ি ১৮, রোড ৭, উত্তরা, ঢাকা ১২৩০, বাংলাদেশ",
                "phone_primary": "+880 1711-000111",
                "phone_secondary": "+880 2-48900000",
                "email": "info@igqs.edu.bd",
                "map_embed_url": "https://www.google.com/maps?q=Uttara+Dhaka&output=embed",
                "office_hours_en": "Sunday–Thursday, 8:00 AM – 4:00 PM",
                "office_hours_bn": "রবিবার–বৃহস্পতিবার, সকাল ৮:০০ – বিকাল ৪:০০",
                "facebook_url": "https://facebook.com",
                "youtube_url": "https://youtube.com",
                "instagram_url": "https://instagram.com",
                "whatsapp_url": "https://wa.me/8801711000111",
                "admission_open": True,
                "admission_announcement_en": "Admissions for the 2026 academic year are now open. Apply online and secure your child's place at IGQS.",
                "admission_announcement_bn": "২০২৬ শিক্ষাবর্ষের ভর্তি চলছে। অনলাইনে আবেদন করে আইজিকিউএস-এ আপনার সন্তানের আসন নিশ্চিত করুন।",
            },
        )

    def _home(self):
        HomeContent.objects.update_or_create(
            pk=1,
            defaults={
                "hero_title_en": "A home of Qur'an, character, and excellence",
                "hero_title_bn": "কুরআন, চরিত্র ও শ্রেষ্ঠত্বের আবাস",
                "hero_subtitle_en": "Ideal Global Qur'anic School prepares students with authentic Islamic knowledge, strong character, and a complete general education.",
                "hero_subtitle_bn": "আদর্শ গ্লোবাল কুরআনিক স্কুল শিক্ষার্থীদের প্রকৃত ইসলামি জ্ঞান, সুদৃঢ় চরিত্র ও পূর্ণাঙ্গ সাধারণ শিক্ষায় গড়ে তোলে।",
                "hero_image_url": IMG["hero"],
                "welcome_en": "Assalamu Alaikum. Welcome to IGQS — a school where the Qur'an is the heart of learning, and every child is guided with care, discipline, and love.",
                "welcome_bn": "আসসালামু আলাইকুম। আইজিকিউএস-এ আপনাকে স্বাগতম — এখানে কুরআনই শিক্ষার কেন্দ্র, আর প্রতিটি শিশু যত্ন, শৃঙ্খলা ও ভালোবাসায় পরিচালিত হয়।",
                "about_preview_en": "IGQS brings together Qur'anic studies, Islamic tarbiyah, and a modern academic curriculum so students grow as confident, compassionate, and capable believers.",
                "about_preview_bn": "আইজিকিউএস কুরআন শিক্ষা, ইসলামি তারবিয়াহ ও আধুনিক একাডেমিক পাঠ্যক্রম একসাথে এনে শিক্ষার্থীদের আত্মবিশ্বাসী, সহমর্মী ও যোগ্য মুমিন হিসেবে গড়ে তোলে।",
                "principal_name_en": "Maulana Abdullah Rahman",
                "principal_name_bn": "মাওলানা আব্দুল্লাহ রহমান",
                "principal_title_en": "Principal",
                "principal_title_bn": "অধ্যক্ষ",
                "principal_message_en": "Our aim is not only academic success, but the formation of hearts that love Allah, respect parents, and serve the community. At IGQS, every lesson begins with sincerity.",
                "principal_message_bn": "আমাদের লক্ষ্য শুধু একাডেমিক সাফল্য নয়, বরং এমন হৃদয় গড়া যা আল্লাহকে ভালোবাসে, পিতা-মাতাকে সম্মান করে এবং সমাজের সেবা করে। আইজিকিউএস-এ প্রতিটি পাঠ শুরু হয় ইখলাস দিয়ে।",
                "principal_photo_url": IMG["principal"],
            },
        )

        WhyChooseItem.objects.all().delete()
        WhyChooseItem.objects.bulk_create(
            [
                WhyChooseItem(
                    title_en="Qur'an at the centre",
                    title_bn="কেন্দ্রে কুরআন",
                    description_en="Daily recitation, memorisation, and understanding of the Qur'an with qualified teachers.",
                    description_bn="যোগ্য শিক্ষকের তত্ত্বাবধানে প্রতিদিন তিলাওয়াত, হিফজ ও কুরআন বোঝার চর্চা।",
                    icon="book-open",
                    order=1,
                ),
                WhyChooseItem(
                    title_en="Balanced curriculum",
                    title_bn="ভারসাম্যপূর্ণ পাঠ্যক্রম",
                    description_en="Islamic studies alongside Bangla, English, mathematics, and science.",
                    description_bn="ইসলামি শিক্ষার পাশাপাশি বাংলা, ইংরেজি, গণিত ও বিজ্ঞান।",
                    icon="layers",
                    order=2,
                ),
                WhyChooseItem(
                    title_en="Character & tarbiyah",
                    title_bn="চরিত্র ও তারবিয়াহ",
                    description_en="Adab, salah, honesty, and leadership are taught as living habits.",
                    description_bn="আদব, সালাত, সততা ও নেতৃত্বকে জীবনের অভ্যাস হিসেবে শেখানো হয়।",
                    icon="heart",
                    order=3,
                ),
                WhyChooseItem(
                    title_en="Caring environment",
                    title_bn="যত্নশীল পরিবেশ",
                    description_en="Small classes, safe campus, and close partnership with guardians.",
                    description_bn="ছোট শ্রেণি, নিরাপদ ক্যাম্পাস এবং অভিভাবকদের সাথে ঘনিষ্ঠ অংশীদারিত্ব।",
                    icon="shield",
                    order=4,
                ),
            ]
        )

    def _about(self):
        AboutPage.objects.update_or_create(
            pk=1,
            defaults={
                "introduction_en": "Ideal Global Qur'anic School (IGQS) is a bilingual Islamic school dedicated to raising a generation rooted in the Qur'an while prepared for the modern world. We combine traditional scholarship with a structured general-education programme.",
                "introduction_bn": "আদর্শ গ্লোবাল কুরআনিক স্কুল (আইজিকিউএস) একটি দ্বিভাষিক ইসলামি বিদ্যালয়, যার লক্ষ্য কুরআনভিত্তিক প্রজন্ম গড়া এবং আধুনিক বিশ্বের জন্য প্রস্তুত করা। আমরা ঐতিহ্যবাহী ইলমের সাথে সুশৃঙ্খল সাধারণ শিক্ষা একত্রিত করি।",
                "vision_en": "To be a leading Qur'anic school that forms knowledgeable, ethical, and confident students who serve their families, ummah, and nation.",
                "vision_bn": "জ্ঞানী, নৈতিক ও আত্মবিশ্বাসী শিক্ষার্থী গড়ে তোলা, যারা পরিবার, উম্মাহ ও জাতির সেবা করবে — এমন একটি অগ্রণী কুরআনিক বিদ্যালয় হওয়া।",
                "mission_en": "Provide excellent Qur'anic and academic education in a safe, spiritually rich environment, partnering with families in the tarbiyah of every child.",
                "mission_bn": "নিরাপদ ও আত্মিক সমৃদ্ধ পরিবেশে উন্নত কুরআন ও একাডেমিক শিক্ষা প্রদান করা এবং প্রতিটি শিশুর তারবিয়াহতে পরিবারের সাথে অংশীদার হওয়া।",
                "history_en": "IGQS began with a small circle of Qur'an students and a clear intention: education that does not separate din from dunya. Over the years the school has grown into a full campus with structured grades, Hifz support, and a vibrant co-curricular life.",
                "history_bn": "আইজিকিউএস শুরু হয়েছিল একটি ছোট কুরআন চক্র ও একটি স্পষ্ট নিয়ত নিয়ে: এমন শিক্ষা যা দ্বীন ও দুনিয়াকে আলাদা করে না। ধীরে ধীরে এটি পূর্ণ ক্যাম্পাস, সুশৃঙ্খল শ্রেণি, হিফজ সহায়তা ও প্রাণবন্ত সহশিক্ষামূলক জীবনে পরিণত হয়েছে।",
                "quranic_approach_en": "Students learn tajweed, memorisation, and meaning. Younger grades focus on fluency and love of recitation; older grades add tafsir, Arabic, and application in daily life. Hifz pathways are available for committed students.",
                "quranic_approach_bn": "শিক্ষার্থীরা তাজবিদ, হিফজ ও অর্থ শেখে। ছোট শ্রেণিতে তিলাওয়াতের সাবলীলতা ও ভালোবাসা; বড় শ্রেণিতে তাফসির, আরবি ও দৈনন্দিন জীবনে প্রয়োগ। প্রতিশ্রুতিবদ্ধ শিক্ষার্থীদের জন্য হিফজ পথ রয়েছে।",
                "principal_message_en": "Guardians are our partners. When home and school walk together upon the Qur'an, children flourish. I invite you to visit the campus, meet our teachers, and see the calm, joyful discipline of IGQS.",
                "principal_message_bn": "অভিভাবকরা আমাদের অংশীদার। ঘর ও স্কুল যখন কুরআনের পথে একসাথে চলে, শিশুরা বিকশিত হয়। ক্যাম্পাস দেখতে, শিক্ষকদের সাথে দেখা করতে এবং আইজিকিউএস-এর শান্ত, আনন্দময় শৃঙ্খলা প্রত্যক্ষ করতে আপনাকে আমন্ত্রণ জানাই।",
            },
        )

        Leader.objects.all().delete()
        Leader.objects.bulk_create(
            [
                Leader(
                    name_en="Maulana Abdullah Rahman",
                    name_bn="মাওলানা আব্দুল্লাহ রহমান",
                    role_en="Principal",
                    role_bn="অধ্যক্ষ",
                    bio_en="Oversees academic quality, tarbiyah, and the school's Qur'anic vision.",
                    bio_bn="একাডেমিক মান, তারবিয়াহ ও বিদ্যালয়ের কুরআনিক দৃষ্টিভঙ্গি তত্ত্বাবধান করেন।",
                    photo_url=IMG["principal"],
                    order=1,
                ),
                Leader(
                    name_en="Ustadha Maryam Hasan",
                    name_bn="উস্তাজা মারইয়াম হাসান",
                    role_en="Head of Qur'anic Studies",
                    role_bn="কুরআন শিক্ষা বিভাগের প্রধান",
                    bio_en="Leads tajweed, Hifz, and Arabic programmes for all grades.",
                    bio_bn="সব শ্রেণির তাজবিদ, হিফজ ও আরবি কার্যক্রম পরিচালনা করেন।",
                    photo_url=IMG["leader2"],
                    order=2,
                ),
                Leader(
                    name_en="Mr. Tariq Islam",
                    name_bn="জনাব তারিক ইসলাম",
                    role_en="Chairman, Managing Committee",
                    role_bn="সভাপতি, পরিচালনা পরিষদ",
                    bio_en="Guides governance, facilities, and long-term development of IGQS.",
                    bio_bn="আইজিকিউএস-এর পরিচালনা, অবকাঠামো ও দীর্ঘমেয়াদি উন্নয়ন পরিচালনা করেন।",
                    photo_url=IMG["leader3"],
                    order=3,
                ),
            ]
        )

        Facility.objects.all().delete()
        Facility.objects.bulk_create(
            [
                Facility(
                    title_en="Qur'an halls",
                    title_bn="কুরআন হল",
                    description_en="Quiet, well-lit spaces for recitation, Hifz circles, and individual practice.",
                    description_bn="তিলাওয়াত, হিফজ হালকা ও ব্যক্তিগত অনুশীলনের জন্য শান্ত, আলোকিত স্থান।",
                    image_url=IMG["quran"],
                    order=1,
                ),
                Facility(
                    title_en="Classrooms",
                    title_bn="শ্রেণিকক্ষ",
                    description_en="Bright classrooms with teaching aids for Bangla, English, maths, and science.",
                    description_bn="বাংলা, ইংরেজি, গণিত ও বিজ্ঞানের জন্য শিক্ষা উপকরণসহ উজ্জ্বল শ্রেণিকক্ষ।",
                    image_url=IMG["classroom"],
                    order=2,
                ),
                Facility(
                    title_en="Library",
                    title_bn="গ্রন্থাগার",
                    description_en="Islamic and general books, reading corners, and supervised study time.",
                    description_bn="ইসলামি ও সাধারণ বই, পড়ার কর্নার এবং তত্ত্বাবধানে অধ্যয়নের সময়।",
                    image_url=IMG["library"],
                    order=3,
                ),
                Facility(
                    title_en="Play & prayer",
                    title_bn="খেলা ও সালাত",
                    description_en="Safe outdoor play, indoor activity space, and a dedicated musalla.",
                    description_bn="নিরাপদ খোলা মাঠ, অভ্যন্তরীণ কার্যক্রম এবং নির্ধারিত মুসা hon।",
                    image_url=IMG["campus"],
                    order=4,
                ),
            ]
        )
        # Fix typo in Bengali - I wrote "মুসা hon" by accident. Let me fix in a follow-up or rewrite that string.
        Facility.objects.filter(title_en="Play & prayer").update(
            description_bn="নিরাপদ খোলা মাঠ, অভ্যন্তরীণ কার্যক্রম এবং নির্ধারিত সালাতের স্থান।"
        )

    def _curriculum(self):
        CurriculumGrade.objects.all().delete()
        grades = [
            {
                "slug": "playgroup",
                "name_en": "Playgroup",
                "name_bn": "প্লেগ্রুপ",
                "description_en": "Gentle introduction to letters, duas, and love of the Qur'an through play.",
                "description_bn": "খেলার মাধ্যমে অক্ষর, দোয়া ও কুরআনের প্রতি ভালোবাসার কোমল সূচনা।",
            },
            {
                "slug": "nursery",
                "name_en": "Nursery",
                "name_bn": "নার্সারি",
                "description_en": "Foundations in recitation, adab, Bangla, English, and early numeracy.",
                "description_bn": "তিলাওয়াত, আদব, বাংলা, ইংরেজি ও প্রাথমিক গণনার ভিত্তি।",
            },
            {
                "slug": "kg",
                "name_en": "Kindergarten",
                "name_bn": "কিন্ডারগার্টেন",
                "description_en": "Tajweed beginnings, short surahs, and a full early-years academic core.",
                "description_bn": "তাজবিদের সূচনা, ছোট সূরা এবং পূর্ণ প্রাক-প্রাথমিক একাডেমিক ভিত্তি।",
            },
            {
                "slug": "class-1",
                "name_en": "Class 1",
                "name_bn": "প্রথম শ্রেণি",
                "description_en": "Structured Qur'an, Islamic studies, and national-curriculum aligned subjects.",
                "description_bn": "সুশৃঙ্খল কুরআন, ইসলামি শিক্ষা এবং জাতীয় পাঠ্যক্রম-সংশ্লিষ্ট বিষয়।",
            },
            {
                "slug": "class-2",
                "name_en": "Class 2",
                "name_bn": "দ্বিতীয় শ্রেণি",
                "description_en": "Fluency in recitation, Arabic letters, and stronger literacy and numeracy.",
                "description_bn": "তিলাওয়াতে সাবলীলতা, আরবি অক্ষর এবং শক্তিশালী সাক্ষরতা ও গণনা।",
            },
            {
                "slug": "class-3",
                "name_en": "Class 3",
                "name_bn": "তৃতীয় শ্রেণি",
                "description_en": "Meaning of selected verses, Islamic manners, and expanding general studies.",
                "description_bn": "নির্বাচিত আয়াতের অর্থ, ইসলামি আদব এবং সম্প্রসারিত সাধারণ শিক্ষা।",
            },
            {
                "slug": "hifz",
                "name_en": "Hifz Programme",
                "name_bn": "হিফজ প্রোগ্রাম",
                "description_en": "Dedicated memorisation track with revision circles and academic support.",
                "description_bn": "পুনরাবৃত্তি হালকা ও একাডেমিক সহায়তাসহ নিবেদিত হিফজ ধারা।",
            },
        ]
        created = []
        for i, g in enumerate(grades, start=1):
            created.append(CurriculumGrade.objects.create(order=i, **g))

        subjects_by_grade = {
            "playgroup": [
                ("Qur'an love & short duas", "কুরআন ভালোবাসা ও ছোট দোয়া", SubjectCategory.QURANIC),
                ("Islamic manners", "ইসলামি আদব", SubjectCategory.ISLAMIC),
                ("Bangla & English play", "বাংলা ও ইংরেজি খেলা", SubjectCategory.GENERAL),
                ("Art & movement", "চিত্রাঙ্কন ও চলাচল", SubjectCategory.COCURRICULAR),
            ],
            "nursery": [
                ("Nazira Qur'an", "নাজিরা কুরআন", SubjectCategory.QURANIC),
                ("Aqidah for children", "শিশুদের আকিদা", SubjectCategory.ISLAMIC),
                ("Bangla, English, Maths", "বাংলা, ইংরেজি, গণিত", SubjectCategory.GENERAL),
                ("Nasheed & story time", "নাশিদ ও গল্পের সময়", SubjectCategory.COCURRICULAR),
            ],
            "kg": [
                ("Tajweed foundations", "তাজবিদের ভিত্তি", SubjectCategory.QURANIC),
                ("Seerah stories", "সিরাতের গল্প", SubjectCategory.ISLAMIC),
                ("Literacy & numeracy", "সাক্ষরতা ও গণনা", SubjectCategory.GENERAL),
                ("Craft & outdoor play", "হস্তশিল্প ও মাঠে খেলা", SubjectCategory.COCURRICULAR),
            ],
            "class-1": [
                ("Qur'an recitation", "কুরআন তিলাওয়াত", SubjectCategory.QURANIC),
                ("Islamic studies", "ইসলামি শিক্ষা", SubjectCategory.ISLAMIC),
                ("Bangla, English, Maths, Science", "বাংলা, ইংরেজি, গণিত, বিজ্ঞান", SubjectCategory.GENERAL),
                ("Sports & drawing", "ক্রীড়া ও অঙ্কন", SubjectCategory.COCURRICULAR),
            ],
            "class-2": [
                ("Hifz support", "হিফজ সহায়তা", SubjectCategory.QURANIC),
                ("Fiqh & adab", "ফিকহ ও আদব", SubjectCategory.ISLAMIC),
                ("Core academics", "মূল একাডেমিক বিষয়", SubjectCategory.GENERAL),
                ("Public speaking", "বক্তৃতা চর্চা", SubjectCategory.COCURRICULAR),
            ],
            "class-3": [
                ("Selected tafsir", "নির্বাচিত তাফসির", SubjectCategory.QURANIC),
                ("Arabic language", "আরবি ভাষা", SubjectCategory.ISLAMIC),
                ("General education", "সাধারণ শিক্ষা", SubjectCategory.GENERAL),
                ("Community service", "সমাজসেবা", SubjectCategory.COCURRICULAR),
            ],
            "hifz": [
                ("New lesson & revision", "নতুন সবরক ও পুনরাবৃত্তি", SubjectCategory.QURANIC),
                ("Tajweed mastery", "তাজবিদ দক্ষতা", SubjectCategory.QURANIC),
                ("Supported academics", "সহায়ক একাডেমিক পাঠ", SubjectCategory.GENERAL),
                ("Character circles", "চরিত্র চর্চার হালকা", SubjectCategory.COCURRICULAR),
            ],
        }
        for grade in created:
            for order, (en, bn, cat) in enumerate(subjects_by_grade[grade.slug], start=1):
                Subject.objects.create(
                    grade=grade,
                    name_en=en,
                    name_bn=bn,
                    category=cat,
                    order=order,
                )
            CurriculumDocument.objects.create(
                title_en=f"{grade.name_en} curriculum outline",
                title_bn=f"{grade.name_bn} পাঠ্যক্রমের রূপরেখা",
                file_url="#",
                grade=grade,
                order=1,
            )

    def _payments(self):
        AdmissionFee.objects.all().delete()
        AdmissionFee.objects.create(amount="15000.00", currency="BDT")
        hifz = CurriculumGrade.objects.filter(slug="hifz").first()
        playgroup = CurriculumGrade.objects.filter(slug="playgroup").first()
        if playgroup:
            AdmissionFee.objects.create(grade=playgroup, amount="12000.00", currency="BDT")
        if hifz:
            AdmissionFee.objects.create(grade=hifz, amount="18000.00", currency="BDT")

        PaymentMethod.objects.all().delete()
        PaymentMethod.objects.bulk_create(
            [
                PaymentMethod(
                    code="bkash",
                    name_en="bKash",
                    name_bn="বিকাশ",
                    account_number="01711-000111",
                    account_name="IGQS Accounts",
                    payment_type_en="Send Money",
                    payment_type_bn="সেন্ড মানি",
                    instructions_en="Open bKash, choose Send Money, pay the admission fee to 01711-000111, then enter the TrxID on this form. Do not use Payment/Merchant without confirmation from the office.",
                    instructions_bn="বিকাশ খুলে সেন্ড মানি নির্বাচন করুন, ০১৭১১-০০০১১১ নম্বরে ভর্তি ফি পাঠান, তারপর এই ফর্মে ট্রানজেকশন আইডি লিখুন। অফিসের নিশ্চিতকরণ ছাড়া পেমেন্ট/মার্চেন্ট ব্যবহার করবেন না।",
                    order=1,
                ),
                PaymentMethod(
                    code="nagad",
                    name_en="Nagad",
                    name_bn="নগদ",
                    account_number="01711-000222",
                    account_name="IGQS Accounts",
                    payment_type_en="Send Money",
                    payment_type_bn="সেন্ড মানি",
                    instructions_en="Send the exact admission fee to the Nagad personal number 01711-000222. Keep the transaction ID from the confirmation SMS.",
                    instructions_bn="নগদ পার্সোনাল নম্বর ০১৭১১-০০০২২২-এ নির্ধারিত ভর্তি ফি পাঠান। নিশ্চিতকরণ এসএমএসের ট্রানজেকশন আইডি সংরক্ষণ করুন।",
                    order=2,
                ),
                PaymentMethod(
                    code="rocket",
                    name_en="Rocket",
                    name_bn="রকেট",
                    account_number="01711000333",
                    account_name="IGQS Accounts",
                    payment_type_en="Send Money",
                    payment_type_bn="সেন্ড মানি",
                    instructions_en="Transfer the admission fee to Rocket 01711000333. Use Send Money and write the student's name in the reference if asked.",
                    instructions_bn="রকেট ০১৭১১০০০৩৩৩-এ ভর্তি ফি পাঠান। সেন্ড মানি ব্যবহার করুন এবং চাইলে রেফারেন্সে শিক্ষার্থীর নাম লিখুন।",
                    order=3,
                ),
                PaymentMethod(
                    code="bank",
                    name_en="Bank Transfer",
                    name_bn="ব্যাংক ট্রান্সফার",
                    account_number="1401200000123",
                    account_name="Ideal Global Qur'anic School",
                    bank_name="Islami Bank Bangladesh PLC, Uttara Branch",
                    payment_type_en="Account deposit / BEFTN",
                    payment_type_bn="একাউন্ট জমা / বিইএফটিএন",
                    instructions_en="Deposit or transfer the admission fee to the school account. Use the student name as the narration, then enter the bank slip / transaction reference on this form.",
                    instructions_bn="স্কুলের হিসাবে ভর্তি ফি জমা বা ট্রান্সফার করুন। বর্ণনায় শিক্ষার্থীর নাম লিখুন, তারপর এই ফর্মে স্লিপ/ট্রানজেকশন রেফারেন্স দিন।",
                    order=4,
                ),
            ]
        )

    def _events(self):
        Event.objects.all().delete()
        now = timezone.now()
        Event.objects.bulk_create(
            [
                Event(
                    slug="quran-competition-2026",
                    title_en="Annual Qur'an Competition",
                    title_bn="বার্ষিক কুরআন প্রতিযোগিতা",
                    start_at=now + timedelta(days=18),
                    location_en="IGQS Main Hall",
                    location_bn="আইজিকিউএস মূল হল",
                    description_en="Students from every grade will recite, compete in tajweed, and share memorised portions. Families are warmly invited.",
                    description_bn="প্রতিটি শ্রেণির শিক্ষার্থী তিলাওয়াত, তাজবিদ ও হিফজ অংশে অংশ নেবে। পরিবারকে সাদর আমন্ত্রণ।",
                    image_url=IMG["quran"],
                ),
                Event(
                    slug="parent-orientation",
                    title_en="New Parent Orientation",
                    title_bn="নতুন অভিভাবক ওরিয়েন্টেশন",
                    start_at=now + timedelta(days=7),
                    location_en="Seminar Room",
                    location_bn="সেমিনার কক্ষ",
                    description_en="Meet teachers, learn daily routines, and understand how home and school work together.",
                    description_bn="শিক্ষকদের সাথে দেখা, দৈনন্দিন রুটিন জানা এবং ঘর ও স্কুলের সহযোগিতা বোঝা।",
                    image_url=IMG["kids"],
                ),
                Event(
                    slug="sports-day",
                    title_en="Sports Day",
                    title_bn="ক্রীড়া দিবস",
                    start_at=now + timedelta(days=40),
                    location_en="Campus Field",
                    location_bn="ক্যাম্পাস মাঠ",
                    description_en="Races, team games, and healthy competition in a respectful Islamic environment.",
                    description_bn="সম্মানজনক ইসলামি পরিবেশে দৌড়, দলগত খেলা ও সুস্থ প্রতিযোগিতা।",
                    image_url=IMG["sports"],
                ),
                Event(
                    slug="milad-gathering",
                    title_en="Seerah Gathering",
                    title_bn="সিরাত সমাবেশ",
                    start_at=now - timedelta(days=25),
                    location_en="School Musalla",
                    location_bn="স্কুল মুসা hon",
                    description_en="Students presented stories from the life of the Prophet ﷺ with nasheed and reflection.",
                    description_bn="শিক্ষার্থীরা নবী ﷺ-এর জীবনের ঘটনা, নাশিদ ও চিন্তা নিয়ে উপস্থাপন করেছে।",
                    image_url=IMG["culture"],
                ),
                Event(
                    slug="science-fair",
                    title_en="Young Explorers Science Fair",
                    title_bn="তরুণ অনুসন্ধানী বিজ্ঞান মেলা",
                    start_at=now - timedelta(days=50),
                    location_en="Classroom Block",
                    location_bn="শ্রেণিকক্ষ ভবন",
                    description_en="A showcase of student projects connecting observation, gratitude, and scientific thinking.",
                    description_bn="পর্যবেক্ষণ, শুকরিয়া ও বৈজ্ঞানিক চিন্তাকে যুক্ত করে শিক্ষার্থীদের প্রকল্প প্রদর্শনী।",
                    image_url=IMG["classroom"],
                ),
            ]
        )
        Event.objects.filter(slug="milad-gathering").update(location_bn="স্কুল সালাতঘর")

    def _news(self):
        NewsPost.objects.all().delete()
        now = timezone.now()
        NewsPost.objects.bulk_create(
            [
                NewsPost(
                    slug="admission-2026-open",
                    title_en="Admission 2026 is open",
                    title_bn="২০২৬ সালের ভর্তি শুরু",
                    category=NewsCategory.ADMISSION,
                    description_en="Guardians may apply online for Playgroup through Class 3 and the Hifz programme. Complete the form, attach documents, and keep your Application ID for follow-up.",
                    description_bn="প্লেগ্রুপ থেকে তৃতীয় শ্রেণি এবং হিফজ প্রোগ্রামে অনলাইনে আবেদন করা যাবে। ফর্ম পূরণ করুন, নথি সংযুক্ত করুন এবং ফলোআপের জন্য আবেদন আইডি সংরক্ষণ করুন।",
                    featured_image_url=IMG["kids"],
                    published_at=now - timedelta(days=2),
                    is_important=True,
                ),
                NewsPost(
                    slug="eid-holiday",
                    title_en="Eid holiday notice",
                    title_bn="ঈদ ছুটির নোটিশ",
                    category=NewsCategory.HOLIDAY,
                    description_en="The campus will remain closed during Eid. Classes resume on the date announced by the office. May Allah accept from us all.",
                    description_bn="ঈদের সময় ক্যাম্পাস বন্ধ থাকবে। অফিস ঘোষিত তারিখে ক্লাস শুরু হবে। আল্লাহ আমাদের সকলের আমল কবুল করুন।",
                    featured_image_url=IMG["campus"],
                    published_at=now - timedelta(days=5),
                    is_important=True,
                ),
                NewsPost(
                    slug="midterm-exam",
                    title_en="Mid-term examination routine",
                    title_bn="অর্ধবার্ষিক পরীক্ষার রুটিন",
                    category=NewsCategory.EXAM,
                    description_en="The mid-term routine has been published for Classes 1–3. Please collect the timetable from the office or download it from the notices board.",
                    description_bn="প্রথম থেকে তৃতীয় শ্রেণির অর্ধবার্ষিক রুটিন প্রকাশিত হয়েছে। অফিস থেকে বা নোটিশ বোর্ড থেকে সময়সূচি সংগ্রহ করুন।",
                    featured_image_url=IMG["library"],
                    published_at=now - timedelta(days=8),
                    is_important=True,
                ),
                NewsPost(
                    slug="new-quran-teachers",
                    title_en="New Qur'an teachers join IGQS",
                    title_bn="নতুন কুরআন শিক্ষক যোগ দিয়েছেন",
                    category=NewsCategory.NEWS,
                    description_en="Two experienced female and male Qur'an teachers have joined to strengthen tajweed and Hifz support this year.",
                    description_bn="তাজবিদ ও হিফজ সহায়তা শক্তিশালী করতে এ বছর দুজন অভিজ্ঞ নারী ও পুরুষ কুরআন শিক্ষক যোগ দিয়েছেন।",
                    featured_image_url=IMG["quran"],
                    published_at=now - timedelta(days=12),
                ),
                NewsPost(
                    slug="campus-safety",
                    title_en="Campus safety update",
                    title_bn="ক্যাম্পাস নিরাপত্তা আপডেট",
                    category=NewsCategory.UPDATE,
                    description_en="Visitor entry is now through the main gate only. Please carry a guardian ID when collecting children.",
                    description_bn="অতিথি প্রবেশ এখন শুধু মূল গেট দিয়ে। সন্তান নেওয়ার সময় অভিভাবক পরিচয়পত্র সাথে রাখুন।",
                    featured_image_url=IMG["campus"],
                    published_at=now - timedelta(days=15),
                    is_important=True,
                ),
                NewsPost(
                    slug="cultural-evening",
                    title_en="Students host a cultural evening",
                    title_bn="শিক্ষার্থীদের সাংস্কৃতিক সন্ধ্যা",
                    category=NewsCategory.ANNOUNCEMENT,
                    description_en="Nasheed, spoken word, and a short play on honesty were presented last Thursday. Photos are in the gallery.",
                    description_bn="গত বৃহস্পতিবার নাশিদ, আবৃত্তি ও সততা বিষয়ক একটি সংক্ষিপ্ত নাটক উপস্থাপিত হয়। ছবি গ্যালারিতে রয়েছে।",
                    featured_image_url=IMG["culture"],
                    published_at=now - timedelta(days=20),
                ),
            ]
        )

    def _gallery(self):
        GalleryAlbum.objects.all().delete()
        albums = [
            (
                "school-activities",
                "School activities",
                "স্কুল কার্যক্রম",
                GalleryCategory.ACTIVITIES,
                IMG["kids"],
                [IMG["kids"], IMG["classroom"], IMG["library"]],
            ),
            (
                "events-album",
                "Events",
                "অনুষ্ঠান",
                GalleryCategory.EVENTS,
                IMG["culture"],
                [IMG["culture"], IMG["quran"], IMG["sports"]],
            ),
            (
                "classroom-life",
                "Classroom activities",
                "শ্রেণিকক্ষের কার্যক্রম",
                GalleryCategory.CLASSROOM,
                IMG["classroom"],
                [IMG["classroom"], IMG["library"], IMG["kids"]],
            ),
            (
                "cultural-programs",
                "Cultural programs",
                "সাংস্কৃতিক অনুষ্ঠান",
                GalleryCategory.CULTURAL,
                IMG["culture"],
                [IMG["culture"], IMG["kids"]],
            ),
            (
                "sports-album",
                "Sports",
                "ক্রীড়া",
                GalleryCategory.SPORTS,
                IMG["sports"],
                [IMG["sports"], IMG["campus"]],
            ),
            (
                "quranic-activities",
                "Islamic & Qur'anic activities",
                "ইসলামি ও কুরআনিক কার্যক্রম",
                GalleryCategory.ISLAMIC,
                IMG["quran"],
                [IMG["quran"], IMG["hero"], IMG["campus"]],
            ),
            (
                "campus-photos",
                "Campus photos",
                "ক্যাম্পাসের ছবি",
                GalleryCategory.CAMPUS,
                IMG["campus"],
                [IMG["campus"], IMG["library"], IMG["quran"]],
            ),
        ]
        for order, (slug, en, bn, cat, cover, images) in enumerate(albums, start=1):
            album = GalleryAlbum.objects.create(
                slug=slug,
                title_en=en,
                title_bn=bn,
                category=cat,
                cover_image_url=cover,
                order=order,
            )
            for i, url in enumerate(images, start=1):
                GalleryImage.objects.create(
                    album=album,
                    image_url=url,
                    caption_en=f"{en} {i}",
                    caption_bn=f"{bn} {i}",
                    order=i,
                )
