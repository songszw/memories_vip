# _*_ coding:utf-8 _*_
from django.shortcuts import render,redirect
from django.contrib.auth import authenticate,login,logout
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q
from django.views.generic.base import View
from django.contrib.auth.hashers import make_password
from django.http import HttpResponse,HttpResponseRedirect
from pure_pagination import Paginator, EmptyPage, PageNotAnInteger
import json
from django.core.urlresolvers import reverse

from .models import UserProfile,EmailVerifyRecord
from .forms import LoginForm,RegisterForm,ForgetForm,ModifyPwdForm,UploadImageForm,UserInfoForm
from utils.email_send import send_register_email
from utils.mixin_utils import LoginRequiredMixin
from operation.models import UserCourse,UserFavorite,UserMessage
from organization.models import CourseOrg,Teacher
from courses.models import Courses
from .models import Banner
# Create your views here.


class CustomBackend(ModelBackend):
# 用户名/邮箱/账号登陆
    def authenticate(self, username=None, password=None, **kwargs):
        try:
            user = UserProfile.objects.get(Q(username = username)|Q(email=username))
            if user.check_password(password):
                return user
        except Exception as e:
            return None


# 登陆
class LoginView(View):
    def get(self,request):
        return render(request, 'login.html', {})

    def post(self,request):
        login_form = LoginForm(request.POST)
        if login_form.is_valid():
            user_name = request.POST.get('username', '')
            pass_word = request.POST.get('password', '')
            user = authenticate(username=user_name, password=pass_word)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    return HttpResponseRedirect(reverse('index'))
                else:
                    return render(request,'login.html',{'msg':'用户未激活'})
            else:
                return render(request, 'login.html', {'msg': '用户名或密码错误'})
        else:
            return render(request, 'login.html', {'logon_form':login_form})


class LogoutView(View):
    # 用户登出
    def get(self,request):
        logout(request)
        return HttpResponseRedirect(reverse('index'))


# 验证用户是否激活
class ActiveUserView(View):
    def get(self,request,active_code):
        all_records = EmailVerifyRecord.objects.filter(code = active_code)
        if all_records:
            for record in all_records:
                email = record.email
                user = UserProfile.objects.get(email=email)
                user.is_active = True
                user.save()
        else:
            return render(request,'active_fail.html')
        return render(request,'login.html')


# 注册
class RegisterView(View):
    def get(self,request):
        register_form = RegisterForm()
        return render(request,'register.html',{'register_form':register_form})

    def post(self,request):
        register_form = RegisterForm(request.POST)
        if register_form.is_valid():
            user_name = request.POST.get('email','')
            if UserProfile.objects.filter(email=user_name):
                return render(request,'register.html',{'register_form':register_form,'msg':'用户名已存在'})
            pass_word = request.POST.get('password','')
            user_profile = UserProfile()
            user_profile.username = user_name
            user_profile.email = user_name
            user_profile.is_active = False
            user_profile.password = make_password(pass_word)
            user_profile.save()

            # 写入欢迎注册消息
            user_message = UserMessage()
            user_message.user = user_profile.id
            user_message.message = '欢迎注册个个的小屋'
            user_message.save()

            send_register_email(user_name,'register')
            return render(request,'login.html')
        else:
            return render(request,'register.html',{'register_form':register_form})


# 忘记密码
class ForgetPwdView(View):
    def get(self,request):
        forget_form = ForgetForm()
        return render(request,'forgetpwd.html',{"forget_form":forget_form})

    def post(self,request):
        forget_form = ForgetForm(request.POST)
        if forget_form.is_valid():
            email = request.POST.get('email','')
            send_register_email(email,'forget')
            return render(request,'send_success.html')
        else:
            return render(request,'forgetpwd.html',{'forget_form':forget_form})


# 重置密码
class ResetView(View):
    def get(self,request,active_code):
        all_records = EmailVerifyRecord.objects.filter(code=active_code)
        if all_records:
            for record in all_records:
                email = record.email
                return render(request,'password_reset.html',{'email':email})
        else:
            return render(request,'active_fail.html')
        return render(request,'login.html')


# 修改密码
class ModifyView(View):
    def post(self,request):
        modify_form = ModifyPwdForm(request.POST)
        if modify_form.is_valid():
            pwd1 = request.POST.get('password1', '')
            pwd2 = request.POST.get('password2', '')
            email = request.POST.get('email', '')
            if pwd1 != pwd2:
                return render(request, 'password_reset.html',{'email': email,'msg': '两次密码不一致'})
            user = UserProfile.objects.get(email = email)
            user.password = make_password(pwd1)
            user.save()
            return render(request,'login.html')
        else:
            email = request.POST.get('email', '')
            return render(request, 'password_reset.html',{'email': email,'modify_form': modify_form})


class UserinfoView(LoginRequiredMixin,View):
    # 用户个人信息
    def get(self,request):
        return render(request,'usercenter-info.html',{})
    def post(self,requset):
        user_info_from = UserInfoForm(requset.POST, instance=requset.user)
        if user_info_from.is_valid():
            user_info_from.save()
            return  HttpResponse('{"status":"success"}',content_type='application/json')
        else:
            return HttpResponse(json.dumps(user_info_from.errors), content_type='application/json')




class UploadImageView(LoginRequiredMixin,View):
    # 用户头像修改
    def post(self,request):
        image_form = UploadImageForm(request.POST,request.FILES,instance=request.user)
        if image_form.is_valid():
            image_form.save()
            return HttpResponse('{"status":"success"}',content_type='application/json')
        else:
            return HttpResponse('{"status":"fail"}',content_type='application/json')


# 个人中心修改密码
class UpdatePwdView(View):
    def post(self,request):
        modify_form = ModifyPwdForm(request.POST)
        if modify_form.is_valid():
            pwd1 = request.POST.get('password1', '')
            pwd2 = request.POST.get('password2', '')
            if pwd1 != pwd2:
                return HttpResponse('{"status":"fail","msg":"两次密码不一致"}', content_type='application/json')
            user = request.user
            user.password = make_password(pwd1)
            user.save()
            return HttpResponse('{"status":"success"}', content_type='application/json')
        else:
            return HttpResponse(json.dumps(modify_form.errors), content_type='application/json')


class SendEmailCodeView(LoginRequiredMixin,View):
    # 发送邮箱验证码
    def get(self,request):
        email = request.GET.get('email','')

        if UserProfile.objects.filter(email=email):
            return HttpResponse('{"email":"邮箱已经存在"}', content_type='application/json')
        send_register_email(email, 'update_email')
        return HttpResponse('{"status":"success"}',content_type='application/json')


class UpdateEmailView(LoginRequiredMixin,View):
    # 修改个人邮箱
    def post(self,request):
        email = request.POST.get('email','')
        code = request.POST.get('code','')

        existed_records = EmailVerifyRecord.objects.filter(email = email, code = code ,send_type ='update_email' )
        if existed_records:
            user = request.user
            user.email = email
            user.save()
            return HttpResponse('{"status":"success"}',content_type='application/json')
        else:
            return HttpResponse('{"email":"验证码出错"}',content_type='application/json')


class MyCourseView(LoginRequiredMixin,View):
    # 我的课程
    def get(self,request):
        user_courses = UserCourse.objects.filter(user=request.user)
        return render(request,'usercenter-mycourse.html',{
            'user_courses':user_courses
        })


class MyFavOrgView(LoginRequiredMixin,View):
    # 我收藏的课程机构
    def get(self,request):
        org_list = []
        fav_orgs = UserFavorite.objects.filter(user = request.user, fav_type=2)
        for fav_org in fav_orgs:
            org_id = fav_org.fav_id
            org =CourseOrg.objects.get(id = org_id)
            org_list.append(org)
        return render(request,'usercenter-fav-org.html',{
            'org_list':org_list
        })


class MyFavTeacherView(LoginRequiredMixin,View):
    # 我收藏的授课讲师
    def get(self,request):
        teacher_list = []
        fav_teachers = UserFavorite.objects.filter(user = request.user, fav_type=3)
        for fav_teacher in fav_teachers:
            teacher_id = fav_teacher.fav_id
            teacher = Teacher.objects.get(id = teacher_id)
            teacher_list.append(teacher)
        return render(request, 'usercenter-fav-teacher.html',{
            'teacher_list':teacher_list
        })


class MyFavCourseView(LoginRequiredMixin,View):
    # 我收藏的课程
    def get(self,request):
        course_list = []
        fav_courses = UserFavorite.objects.filter(user = request.user, fav_type=1)
        for fav_course in fav_courses:
            course_id = fav_course.fav_id
            course = Courses.objects.get(id = course_id)
            course_list.append(course)
        return render(request, 'usercenter-fav-course.html',{
            'course_list':course_list
        })


class MyMessageView(LoginRequiredMixin,View):
    # 我的消息
    def get(self,request):
        all_message = UserMessage.objects.filter(user=request.user.id)
        all_unread_messages = UserMessage.objects.filter(user = request.user.id ,has_read=False)
        for unread_message in all_unread_messages:
            unread_message.has_read = True
            unread_message.save()
        # 分页
        try:
            page = request.GET.get('page', 1)
        except PageNotAnInteger:
            page = 1
        p = Paginator(all_message, 1, request=request)
        messages = p.page(page)

        return render(request,'usercenter-message.html',{
            'messages':messages,

        })


class IndexView(View):
    # 个个的小屋首页
    def get(self,request):
        # 轮播图
        all_banners = Banner.objects.all().order_by('index')
        courses = Courses.objects.filter(is_banner = False)[:6]
        banner_courses = Courses.objects.filter(is_banner = False)[:3]
        course_orgs = CourseOrg.objects.all()[:15]
        return render(request,'index.html',{
            'all_banners':all_banners,
            'courses':courses,
            'banner_courses':banner_courses,
            'course_orgs':course_orgs
        })


def page_not_found(request):
    # 全局404处理函数
    from django.shortcuts import render_to_response
    response = render_to_response('404.html',{})
    response.status_code = 404
    return response


def page_error(request):
    # 全局500处理函数
    from django.shortcuts import render_to_response
    response = render_to_response('500.html',{})
    response.status_code = 500
    return response