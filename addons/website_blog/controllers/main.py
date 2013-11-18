# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2013-Today OpenERP SA (<http://www.openerp.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp.addons.website.models import website
from openerp.tools.translate import _

import werkzeug


class WebsiteBlog(http.Controller):
    _category_post_per_page = 6
    _post_comment_per_page = 6

    def nav_list(self):
        blog_post_obj = request.registry['blog.post']
        groups = blog_post_obj.read_group(request.cr, request.uid, [], ['name', 'create_date'], 
            groupby="create_date", orderby="create_date asc", context=request.context)
        for group in groups:
            group['date'] = "%s_%s" % (group['__domain'][0][2], group['__domain'][1][2])
        return groups

    @website.route([
        '/blog',
        '/blog/page/<int:page>/',
    ], type='http', auth="public", multilang=True)
    def blogs(self, page=1):
        BYPAGE = 60
        cr, uid, context = request.cr, request.uid, request.context
        blog_obj = request.registry['blog.post']
        total = blog_obj.search(cr, uid, [], count=True, context=context)
        pager = request.website.pager(
            url='/blog/',
            total=total,
            page=page,
            step=BYPAGE,
        )
        bids = blog_obj.search(cr, uid, [], offset=(page-1)*BYPAGE, limit=BYPAGE, context=context)
        blogs = blog_obj.browse(cr, uid, bids, context=context)
        return request.website.render("website_blog.latest_blogs", {
            'blogs': blogs,
            'pager': pager
        })

    @website.route([
        '/blog',
        '/blog/page/<int:page>/',
        '/blog/cat/<model("blog.category"):category>/',
        '/blog/cat/<model("blog.category"):category>/page/<int:page>/',
        '/blog/tag/<model("blog.tag"):tag>/',
        '/blog/tag/<model("blog.tag"):tag>/page/<int:page>/',
        '/blog/cat/<model("blog.category"):category>/date/<string(length=21):date>/',
        '/blog/tag/<model("blog.tag"):tag>/date/<string(length=21):date>/',
        '/blog/tag/<model("blog.tag"):tag>/date/<string(length=21):date>/page/<int:page>/',
    ], type='http', auth="public", multilang=True)
    def blog(self, category=None, tag=None, page=1, date=None):
        """ Prepare all values to display the blog.

        :param category: category currently browsed.
        :param tag: tag that is currently used to filter blog posts
        :param integer page: current page of the pager. Can be the category or
                            post pager.
        :param date: date currently used to filter blog posts (dateBegin_dateEnd)

        :return dict values: values for the templates, containing

         - 'blog_posts': list of browse records that are the posts to display
                         in a given category, if not blog_post_id
         - 'category': browse of the current category, if category_id
         - 'categories': list of browse records of categories
         - 'pager': the pager to display posts pager in a category
         - 'tag': current tag, if tag_id
         - 'nav_list': a dict [year][month] for archives navigation
        """
        BYPAGE = 10

        cr, uid, context = request.cr, request.uid, request.context
        blog_post_obj = request.registry['blog.post']

        blog_posts = None

        category_obj = request.registry['blog.category']
        category_ids = category_obj.search(cr, uid, [], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context)

        path_filter = ""
        domain = []

        if category:
            path_filter += "cat/%s/" % category.id
            domain += [("id", "=", [blog.id for blog in category.blog_post_ids])]
        if tag:
            path_filter += 'tag/%s/' % tag.id
            domain += [("id", "=", [blog.id for blog in tag.blog_post_ids])]
        if date:
            path_filter += "date/%s/" % date
            date = date.split("_")
            domain = [("create_date", ">=", date[0]), ("create_date", "<=", date[1])]

        blog_post_ids = blog_post_obj.search(cr, uid, domain, context=context)
        blog_posts = blog_post_obj.browse(cr, uid, blog_post_ids, context=context)

        pager = request.website.pager(
            url="/blog/%s" % path_filter,
            total=len(blog_posts),
            page=page,
            step=self._category_post_per_page,
            scope=BYPAGE
        )
        pager_begin = (page - 1) * self._category_post_per_page
        pager_end = page * self._category_post_per_page
        blog_posts = blog_posts[pager_begin:pager_end]

        values = {
            'category': category,
            'categories': categories,
            'tag': tag,
            'blog_posts': blog_posts,
            'pager': pager,
            'nav_list': self.nav_list(),
            'path_filter': path_filter,
        }

        if tag:
            values['main_object'] = tag
        elif category:
            values['main_object'] = category

        return request.website.render("website_blog.blog_post_short", values)

    @website.route([
        '/blog/<model("blog.post"):blog_post>/page/<int:page>/',
        '/blog/<model("blog.post"):blog_post>/cat/<model("blog.category"):category>/',
        '/blog/<model("blog.post"):blog_post>/cat/<model("blog.category"):category>/page/<int:page>/',
        '/blog/<model("blog.post"):blog_post>/tag/<model("blog.tag"):tag>/',
        '/blog/<model("blog.post"):blog_post>/tag/<model("blog.tag"):tag>/page/<int:page>/',
        '/blog/<model("blog.post"):blog_post>/cat/<model("blog.category"):category>/date/<string(length=21):date>/',
        '/blog/<model("blog.post"):blog_post>/tag/<model("blog.tag"):tag>/date/<string(length=21):date>/',
        '/blog/<model("blog.post"):blog_post>/tag/<model("blog.tag"):tag>/date/<string(length=21):date>/page/<int:page>/',
    ], type='http', auth="public", multilang=True)
    def blog_post(self, blog_post=None, category=None, tag=None, page=1, date=None, enable_editor=None, path_filter=''):
        """ Prepare all values to display the blog.

        :param blog_post: blog post currently browsed. If not set, the user is
                          browsing the category and a post pager is calculated.
                          If set the user is reading the blog post and a
                          comments pager is calculated.
        :param category: category currently browsed.
        :param tag: tag that is currently used to filter blog posts
        :param integer page: current page of the pager. Can be the category or
                            post pager.
        :param date: date currently used to filter blog posts (dateBegin_dateEnd)

         - 'enable_editor': editor control

        :return dict values: values for the templates, containing

         - 'blog_post': browse of the current post, if blog_post_id
         - 'category': browse of the current category, if category_id
         - 'categories': list of browse records of categories
         - 'pager': the pager to display comments pager in a blog post
         - 'tag': current tag, if tag_id
         - 'nav_list': a dict [year][month] for archives navigation
        """

        pager_url = "/blog/%s" % blog_post.id

        if path_filter:
            pager_url += path_filter

        pager = request.website.pager(
            url=pager_url,
            total=len(blog_post.website_message_ids),
            page=page,
            step=self._post_comment_per_page,
            scope=7
        )
        pager_begin = (page - 1) * self._post_comment_per_page
        pager_end = page * self._post_comment_per_page
        blog_post.website_message_ids = blog_post.website_message_ids[pager_begin:pager_end]

        cr, uid, context = request.cr, request.uid, request.context
        category_obj = request.registry['blog.category']
        category_ids = category_obj.search(cr, uid, [], context=context)
        categories = category_obj.browse(cr, uid, category_ids, context=context)

        values = {
            'category': category,
            'categories': categories,
            'tag': tag,
            'blog_post': blog_post,
            'pager': pager,
            'nav_list': self.nav_list(),
            'enable_editor': enable_editor,
            'path_filter': path_filter,
        }
        return request.website.render("website_blog.blog_post_complete", values)

    @website.route(['/blog/<int:blog_post_id>/comment'], type='http', auth="public")
    def blog_post_comment(self, blog_post_id=None, **post):
        cr, uid, context = request.cr, request.uid, request.context
        if post.get('comment'):
            request.registry['blog.post'].message_post(
                cr, uid, blog_post_id,
                body=post.get('comment'),
                type='comment',
                subtype='mt_comment',
                context=dict(context, mail_create_nosubcribe=True))
        return werkzeug.utils.redirect(request.httprequest.referrer + "#comments")

    @website.route(['/blog/<int:category_id><path:path_filter>/new'], type='http', auth="public", multilang=True)
    def blog_post_create(self, category_id=None, path_filter='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].create(
            request.cr, request.uid, {
                'category_id': category_id,
                'name': _("Blog title"),
                'content': '',
                'website_published': False,
            }, context=create_context)
        return werkzeug.utils.redirect("/blog/%s%s/?enable_editor=1" % (new_blog_post_id, path_filter))

    @website.route(['/blog/<int:blog_post_id><path:path_filter>/duplicate'], type='http', auth="public")
    def blog_post_copy(self, blog_post_id=None, path_filter='', **post):
        cr, uid, context = request.cr, request.uid, request.context
        create_context = dict(context, mail_create_nosubscribe=True)
        new_blog_post_id = request.registry['blog.post'].copy(cr, uid, blog_post_id, {}, context=create_context)
        return werkzeug.utils.redirect("/blog/%s%s/?enable_editor=1" % (new_blog_post_id, path_filter))
