# _*_ encoding:utf-8 _*_
from django.shortcuts import render
from django.views.generic.base import View
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger
from django.http import HttpResponse
from django.db.models import Q

from .models import Courses, CourseResource,Video
from operation.models import UserFavorite, CourseComments,UserCourse
from utils.mixin_utils import LoginRequiredMixin

# Create your views here.


class CourseListView(View):
    def get(self, request):
        current_page='course'

        all_courses = Courses.objects.all().order_by('-add_time')

        hot_courses = Courses.objects.all().order_by('-click_nums')[:3]

        # 课程搜索
        search_keywords = request.GET.get('keywords','')
        if search_keywords:
            all_courses = all_courses.filter(Q(name__icontains=search_keywords)|Q(detail__icontains=search_keywords)|Q(desc__icontains=search_keywords))

        # 排序
        sort = request.GET.get('sort', '')
        if sort:
            if sort == 'students':
                all_courses = all_courses.order_by('-students')
            elif sort == 'hot':
                all_courses = all_courses.order_by('-click_nums')

        # 分页
        try:
            page = request.GET.get('page', 1)
        except PageNotAnInteger:
            page = 1
        p = Paginator(all_courses, 6, request=request)
        courses = p.page(page)

        return render(request, 'course-list.html', {
            'all_courses': courses,
            'sort': sort,
            'hot_courses': hot_courses,
            'current_page': current_page
        })


class CourseDetailView(View):
    # 课程详情页
    def get(self, request, course_id):
        course = Courses.objects.get(id=int(course_id))
        # 增加课程点击数
        course.click_nums += 1
        course.save()

        has_fav_course = False
        has_fav_org = False

        if request.user.is_authenticated():
            if UserFavorite.objects.filter(user = request.user, fav_id=course.id, fav_type=1):
                has_fav_course = True

            if UserFavorite.objects.filter(user = request.user, fav_id=course.course_org.id, fav_type=2):
                has_fav_org = True

        tag = course.tag
        if tag:
            relate_coures = Courses.objects.filter(tag = tag)[:1]
        else:
            relate_coures = []

        return render(request, 'course-detail.html', {
            'course':course, 
            'relate_coures':relate_coures, 
            'has_fav_course':has_fav_course, 
            'has_fav_org':has_fav_org
        })


class CourseInfoView(LoginRequiredMixin,View):
    # 课程章节信息
    def get(self, request, course_id):
        course = Courses.objects.get(id=int(course_id))
        course.students += 1
        course.save()

        # 查询用户是否已经关联该课程
        user_courses = UserCourse.objects.filter(user=request.user, course=course)
        if not user_courses:
            user_course = UserCourse(user=request.user, course=course)
            user_course.save()
        user_cousers = UserCourse.objects.filter(course=course)
        user_ids = [user_couser.user.id for user_couser in user_cousers]
        all_user_courses = UserCourse.objects.filter(user_id__in=user_ids)
        # 取出所有课程id
        course_ids = [user_couser.course.id for user_couser in all_user_courses]
        # 获取学过该用户学过其他的课程
        relate_courses = Courses.objects.filter(id__in=course_ids).order_by('-click_nums')[:5]

        all_resources = CourseResource.objects.filter(course = course)
        return render(request, 'course-video.html', {
            'course':course, 
            'course_resources':all_resources,
            'relate_courses':relate_courses
        })


class CourseCommentView(LoginRequiredMixin,View):
    # 课程评论
    def get(self, request, course_id):
        course = Courses.objects.get(id=int(course_id))
        user_cousers = UserCourse.objects.filter(course=course)
        user_ids = [user_couser.user.id for user_couser in user_cousers]
        all_user_courses = UserCourse.objects.filter(user_id__in=user_ids)
        # 取出所有课程id
        course_ids = [user_couser.course.id for user_couser in all_user_courses]
        # 获取学过该用户学过其他的课程
        relate_courses = Courses.objects.filter(id__in=course_ids).order_by('-click_nums')[:5]
        all_resources = CourseResource.objects.filter(course=course)
        all_comments = CourseComments.objects.filter(course_id=course)
        return render(request, 'course-comment.html', {
            'course': course, 
            'course_resourses': all_resources, 
            'all_comments':all_comments,
            'relate_courses':relate_courses
        })


class AddCommentView(View):
    # 用户添加课程评论
    def post(self, request):
        # 首先判断用户是否已登陆
        if not request.user.is_authenticated():
            return HttpResponse('{"status":"fail", "msg":"用户未登录"}', content_type='application/json')

        course_id = request.POST.get('course_id', 0)
        comments = request.POST.get('comments', '')
        if course_id > 0 and comments:
            course_comments = CourseComments()
            course = Courses.objects.get(id = int(course_id))
            course_comments.course = course
            course_comments.comments = comments
            course_comments.user = request.user
            course_comments.save()
            return HttpResponse('{"status":"success", "msg":"添加成功"}', content_type='application/json')
        else:
            return HttpResponse('{"status":"success", "msg":"添加失败"}', content_type='application/json')


class VideoPlayView(View):
    # 视频播放页面
    def get(self, request, video_id):
        video = Video.objects.get(id=int(video_id))
        course = video.lesson.courses
        course.students += 1
        course.save()

        # 查询用户是否已经关联该课程
        user_courses = UserCourse.objects.filter(user=request.user, course=course)
        if not user_courses:
            user_course = UserCourse(user=request.user, course=course)
            user_course.save()
        user_cousers = UserCourse.objects.filter(course=course)
        user_ids = [user_couser.user.id for user_couser in user_cousers]
        all_user_courses = UserCourse.objects.filter(user_id__in=user_ids)
        # 取出所有课程id
        course_ids = [user_couser.course.id for user_couser in all_user_courses]
        # 获取学过该用户学过其他的课程
        relate_courses = Courses.objects.filter(id__in=course_ids).order_by('-click_nums')[:5]

        all_resources = CourseResource.objects.filter(course = course)
        return render(request, 'course-play.html', {
            'course':course,
            'course_resources':all_resources,
            'relate_courses':relate_courses,
            'video':video
        })