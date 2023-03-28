# -*- coding: utf-8 -*-

import uuid
import datetime

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, UserManager

from django.db import models
from django.utils.translation import gettext_lazy as _


class coustomUserManager(UserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user


    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)


    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    """
    ユーザクラス
    """
    uuid = models.UUIDField(verbose_name=_('uuid'), 
                primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(verbose_name=_('user name'), 
                max_length=20, default='guestuser')
    email = models.EmailField(verbose_name=_('email address'), unique=True)
    create_date = models.DateTimeField(
                verbose_name=_('create date'), default=datetime.datetime.now())
    update_date = models.DateTimeField(
                verbose_name=_('update date'), null=True, blank=True)
    delete_flag = models.BooleanField(
                verbose_name=_('delete flag'), default=False)

    is_staff = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=True)
    is_superuser = models.BooleanField(default=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = coustomUserManager()


    @property
    def is_staff_property(self):
        return self.is_admin


    @property
    def is_superuser_property(self):
        return self.is_admin


    def __str__(self):
        return self.username
