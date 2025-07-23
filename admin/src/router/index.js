import Vue from 'vue'
import Router from 'vue-router'

Vue.use(Router)

/* Layout */
import Layout from '@/layout'

/* Router Modules */
import componentsRouter from './modules/components'
import chartsRouter from './modules/charts'
import tableRouter from './modules/table'
import nestedRouter from './modules/nested'

/**
 * Note: sub-menu only appear when route children.length >= 1
 * Detail see: https://panjiachen.github.io/vue-element-admin-site/guide/essentials/router-and-nav.html
 *
 * hidden: true                   if set true, item will not show in the sidebar(default is false)
 * alwaysShow: true               if set true, will always show the root menu
 *                                if not set alwaysShow, when item has more than one children route,
 *                                it will becomes nested mode, otherwise not show the root menu
 * redirect: noRedirect           if set noRedirect will no redirect in the breadcrumb
 * name:'router-name'             the name is used by <keep-alive> (must set!!!)
 * meta : {
    roles: ['admin','editor']    control the page roles (you can set multiple roles)
    title: 'title'               the name show in sidebar and breadcrumb (recommend set)
    icon: 'svg-name'/'el-icon-x' the icon show in the sidebar
    noCache: true                if set true, the page will no be cached(default is false)
    affix: true                  if set true, the tag will affix in the tags-view
    breadcrumb: false            if set false, the item will hidden in breadcrumb(default is true)
    activeMenu: '/example/list'  if set path, the sidebar will highlight the path you set
  }
 */

/**
 * constantRoutes
 * a base page that does not have permission requirements
 * all roles can be accessed
 */
export const constantRoutes = [
  {
    path: '/redirect',
    component: Layout,
    hidden: true,
    children: [
      {
        path: '/redirect/:path(.*)',
        component: () => import('@/views/redirect/index')
      }
    ]
  },
  {
    path: '/login',
    component: () => import('@/views/login/index'),
    hidden: true
  },
  {
    path: '/auth-redirect',
    component: () => import('@/views/login/auth-redirect'),
    hidden: true
  },
  {
    path: '/404',
    component: () => import('@/views/error-page/404'),
    hidden: true
  },
  {
    path: '/401',
    component: () => import('@/views/error-page/401'),
    hidden: true
  },
  {
    path: '/',
    component: Layout,
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        component: () => import('@/views/dashboard/index'),
        name: 'Dashboard',
        meta: { title: 'Dashboard', icon: 'dashboard', affix: true }
      }
    ]
  },
  {
    path: '/documentation',
    component: Layout,
    children: [
      {
        path: 'index',
        component: () => import('@/views/documentation/index'),
        name: 'Documentation',
        meta: { title: 'Documentation', icon: 'documentation', affix: true }
      }
    ]
  },
  {
    path: '/guide',
    component: Layout,
    redirect: '/guide/index',
    children: [
      {
        path: 'index',
        component: () => import('@/views/guide/index'),
        name: 'Guide',
        meta: { title: 'Guide', icon: 'guide', noCache: true }
      }
    ]
  },
  {
    path: '/profile',
    component: Layout,
    redirect: '/profile/index',
    hidden: true,
    children: [
      {
        path: 'index',
        component: () => import('@/views/profile/index'),
        name: 'Profile',
        meta: { title: 'Profile', icon: 'user', noCache: true }
      }
    ]
  }
]

/**
 * asyncRoutes
 * the routes that need to be dynamically loaded based on user roles
 */
export const asyncRoutes = [
  {
    path: '/permission',
    component: Layout,
    redirect: '/permission/page',
    alwaysShow: true, // will always show the root menu
    name: 'Permission',
    meta: {
      title: 'Permission',
      icon: 'lock',
      roles: ['admin', 'editor'] // you can set roles in root nav
    },
    children: [
      {
        path: 'page',
        component: () => import('@/views/permission/page'),
        name: 'PagePermission',
        meta: {
          title: 'Page Permission',
          roles: ['admin'] // or you can only set roles in sub nav
        }
      },
      {
        path: 'directive',
        component: () => import('@/views/permission/directive'),
        name: 'DirectivePermission',
        meta: {
          title: 'Directive Permission'
          // if do not set roles, means: this page does not require permission
        }
      },
      {
        path: 'role',
        component: () => import('@/views/permission/role'),
        name: 'RolePermission',
        meta: {
          title: 'Role Permission',
          roles: ['admin']
        }
      }
    ]
  },

  {
    path: '/icon',
    component: Layout,
    children: [
      {
        path: 'index',
        component: () => import('@/views/icons/index'),
        name: 'Icons',
        meta: { title: 'Icons', icon: 'icon', noCache: true }
      }
    ]
  },

  /** when your routing map is too long, you can split it into small modules **/
  componentsRouter,
  chartsRouter,
  nestedRouter,
  tableRouter,

  {
    path: '/exam',
    component: Layout,
    redirect: '/exam/examlist',
    name: '考试',
    meta: { title: '考试', icon: 'el-icon-document' },
    children: [
      {
        path: 'examlist',
        component: () => import('@/views/exam/examlist'),
        name: '考试列表',
        meta: { title: '考试管理', icon: 'list' }
      },
      {
        path: 'editexam/:id?',
        component: () => import('@/views/exam/editexam'),
        name: '编辑考试',
        meta: { title: '编辑考试', noCache: true, activeMenu: '/exam/examlist' },
        hidden: true
      },
      {
        path: 'studentlist/:exam_id',
        component: () => import('@/views/exam/studentlist'),
        name: '考试学生列表',
        meta: { title: '考试学生', noCache: true, activeMenu: '/exam/examlist' },
        hidden: true
      },
      {
        path: 'questionlist/:exam_id',
        component: () => import('@/views/exam/questionlist'),
        name: '考试题目列表',
        meta: { title: '考试题目', noCache: true, activeMenu: '/exam/examlist' },
        hidden: true
      },
      {
        path: 'editquestion/:exam_id/:question_id?',
        component: () => import('@/views/exam/editquestion'),
        name: '编辑题目',
        meta: { title: '编辑题目', noCache: true, activeMenu: '/exam/examlist' },
        hidden: true
      }
    ]
  },

  {
    path: '/example',
    component: Layout,
    redirect: '/example/list',
    name: '内容',
    meta: {
      title: '内容',
      icon: 'el-icon-s-help'
    },
    children: [
      {
        path: 'create',
        component: () => import('@/views/example/create'),
        name: '添加内容',
        meta: { title: '添加内容', icon: 'edit', activeMenu: '/example/list'  },
        hidden: true
      },
      {
        path: 'edit/:id(\\d+)',
        component: () => import('@/views/example/edit'),
        name: '编辑内容',
        meta: { title: '编辑内容', noCache: true, activeMenu: '/example/list' },
        hidden: true
      },
      {
        path: 'list',
        component: () => import('@/views/example/list'),
        name: '内容列表',
        meta: { title: '内容管理', icon: 'list' }
      }
      ,{
        path: 'createcity',
        component: () => import('@/views/example/createcity'),
        name: '添加城市',
        meta: { title: '添加城市', icon: 'edit', activeMenu: '/example/citylist' },
        hidden: true
      },{
        path: 'editcity/:id(\\d+)',
        component: () => import('@/views/example/editcity'),
        name: '编辑城市',
        meta: { title: '编辑城市', noCache: true, activeMenu: '/example/citylist' },
        hidden: true
      },{
        path: 'citylist',
        component: () => import('@/views/example/citylist'),
        name: '城市列表',
        meta: { title: '城市管理', icon: 'list' }
      }
      ,{
        path: 'createarea',
        component: () => import('@/views/example/createarea'),
        name: '添加社区',
        meta: { title: '添加社区', icon: 'edit', activeMenu: '/example/arealist' },
        hidden: true
      },{
        path: 'editarea/:id(\\d+)',
        component: () => import('@/views/example/editarea'),
        name: '编辑社区',
        meta: { title: '编辑社区', noCache: true, activeMenu: '/example/arealist' },
        hidden: true
      },{
        path: 'arealist',
        component: () => import('@/views/example/arealist'),
        name: '社区列表',
        meta: { title: '社区管理', icon: 'list' }
      }
      ,{
        path: 'createcell',
        component: () => import('@/views/example/createcell'),
        name: '添加单元',
        meta: { title: '添加单元', icon: 'edit',activeMenu: '/example/celllist'  },
        hidden: true
      },{
        path: 'editcell/:id(\\d+)',
        component: () => import('@/views/example/editcell'),
        name: '编辑单元',
        meta: { title: '编辑单元', noCache: true, activeMenu: '/example/celllist' },
        hidden: true
      },{
        path: 'celllist',
        component: () => import('@/views/example/celllist'),
        name: '单元管理',
        meta: { title: '单元管理', icon: 'list' }
      }
      ,{
        path: 'createcomment',
        component: () => import('@/views/example/createcomment'),
        name: '添加评论',
        meta: { title: '添加评论', noCache: true, activeMenu: '/example/commentlist' },
        hidden: true
      }
      ,{
        path: 'editcomment/:id(\\d+)',
        component: () => import('@/views/example/editcomment'),
        name: '编辑评论',
        meta: { title: '编辑评论', noCache: true, activeMenu: '/example/commentlist' },
        hidden: true
      },{
        path: 'commentlist',
        component: () => import('@/views/example/commentlist'),
        name: '评论管理',
        meta: { title: '评论管理', icon: 'list' }
      }
      ,{
        path: 'createreply',
        component: () => import('@/views/example/createreply'),
        name: '添加回复',
        meta: { title: '添加回复', noCache: true, activeMenu: '/example/replylist' },
        hidden: true
      }
      ,{
        path: 'editreply/:id(\\d+)',
        component: () => import('@/views/example/editreply'),
        name: '编辑回复',
        meta: { title: '编辑回复', noCache: true, activeMenu: '/example/replylist' },
        hidden: true
      }
      ,{
        path: 'replylist',
        component: () => import('@/views/example/replylist'),
        name: '回复管理',
        meta: { title: '回复管理', icon: 'list' }
      }
      ,{
        path: 'userlist',
        component: () => import('@/views/example/userlist'),
        name: '用户管理',
        meta: { title: '用户管理', icon: 'list' }
      }
      ,{
        path: 'createuser',
        component: () => import('@/views/example/createuser'),
        name: '添加用户',
        meta: { title: '添加用户', noCache: true, activeMenu: '/example/userlist' },
        hidden: true
      }
      ,{
        path: 'edituser/:id(\\d+)',
        component: () => import('@/views/example/edituser'),
        name: '编辑用户',
        meta: { title: '编辑用户', noCache: true, activeMenu: '/example/userlist' },
        hidden: true
      }
    ]
  },

  {
    path: '/tab',
    component: Layout,
    children: [
      {
        path: 'index',
        component: () => import('@/views/tab/index'),
        name: 'Tab',
        meta: { title: 'Tab', icon: 'tab' }
      }
    ]
  },

  {
    path: '/error',
    component: Layout,
    redirect: 'noRedirect',
    name: 'ErrorPages',
    meta: {
      title: 'Error Pages',
      icon: '404'
    },
    children: [
      {
        path: '401',
        component: () => import('@/views/error-page/401'),
        name: 'Page401',
        meta: { title: '401', noCache: true }
      },
      {
        path: '404',
        component: () => import('@/views/error-page/404'),
        name: 'Page404',
        meta: { title: '404', noCache: true }
      }
    ]
  },

  {
    path: '/error-log',
    component: Layout,
    children: [
      {
        path: 'log',
        component: () => import('@/views/error-log/index'),
        name: 'ErrorLog',
        meta: { title: 'Error Log', icon: 'bug' }
      }
    ]
  },

  {
    path: '/excel',
    component: Layout,
    redirect: '/excel/export-excel',
    name: 'Excel',
    meta: {
      title: 'Excel',
      icon: 'excel'
    },
    children: [
      {
        path: 'export-excel',
        component: () => import('@/views/excel/export-excel'),
        name: 'ExportExcel',
        meta: { title: 'Export Excel' }
      },
      {
        path: 'export-selected-excel',
        component: () => import('@/views/excel/select-excel'),
        name: 'SelectExcel',
        meta: { title: 'Export Selected' }
      },
      {
        path: 'export-merge-header',
        component: () => import('@/views/excel/merge-header'),
        name: 'MergeHeader',
        meta: { title: 'Merge Header' }
      },
      {
        path: 'upload-excel',
        component: () => import('@/views/excel/upload-excel'),
        name: 'UploadExcel',
        meta: { title: 'Upload Excel' }
      }
    ]
  },

  {
    path: '/zip',
    component: Layout,
    redirect: '/zip/download',
    alwaysShow: true,
    name: 'Zip',
    meta: { title: 'Zip', icon: 'zip' },
    children: [
      {
        path: 'download',
        component: () => import('@/views/zip/index'),
        name: 'ExportZip',
        meta: { title: 'Export Zip' }
      }
    ]
  },

  {
    path: '/pdf',
    component: Layout,
    redirect: '/pdf/index',
    children: [
      {
        path: 'index',
        component: () => import('@/views/pdf/index'),
        name: 'PDF',
        meta: { title: 'PDF', icon: 'pdf' }
      }
    ]
  },
  {
    path: '/pdf/download',
    component: () => import('@/views/pdf/download'),
    hidden: true
  },

  {
    path: '/theme',
    component: Layout,
    children: [
      {
        path: 'index',
        component: () => import('@/views/theme/index'),
        name: 'Theme',
        meta: { title: 'Theme', icon: 'theme' }
      }
    ]
  },

  {
    path: '/clipboard',
    component: Layout,
    children: [
      {
        path: 'index',
        component: () => import('@/views/clipboard/index'),
        name: 'ClipboardDemo',
        meta: { title: 'Clipboard', icon: 'clipboard' }
      }
    ]
  },

  {
    path: 'external-link',
    component: Layout,
    children: [
      {
        path: 'https://github.com/PanJiaChen/vue-element-admin',
        meta: { title: 'External Link', icon: 'link' }
      }
    ]
  },


  // 404 page must be placed at the end !!!
  { path: '*', redirect: '/404', hidden: true }
]

const createRouter = () => new Router({
  // mode: 'history', // require service support
  scrollBehavior: () => ({ y: 0 }),
  routes: constantRoutes
})

const router = createRouter()

// Detail see: https://github.com/vuejs/vue-router/issues/1234#issuecomment-357941465
export function resetRouter() {
  const newRouter = createRouter()
  router.matcher = newRouter.matcher // reset router
}

export default router
