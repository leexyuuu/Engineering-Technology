<template>
  <div class="createPost-container">
    <el-form ref="postForm" :model="postForm" :rules="rules" class="form-container">

      <sticky :z-index="10" :class-name="'sub-navbar '+postForm.status">
        <CommentDropdown v-model="postForm.comment_disabled" />
        <StatusDropdown v-model="postForm.status" />
        <TypeDropdown v-model="postForm.type" />
      
        <el-button v-loading="loading" style="margin-left: 10px;" type="success" @click="submitForm">
          发布
        </el-button>
      
      </sticky>

      <div class="createPost-main-container">
        <el-row>
       
          <el-col :span="24">
            <el-form-item style="margin-bottom: 40px;" prop="title">
              <MDinput v-model="postForm.title" :maxlength="100" name="标题" required>
                标题
              </MDinput>
            </el-form-item>

            <div class="postInfo-container">
              <el-row>
                <el-col :span="6"  >
                <el-form-item label-width="60px" label="类型" class="postInfo-container-item">
                  <el-select v-model="postForm.type"  filterable default-first-option>
                    <el-option v-for="(item, index) in typeOptions" :key="item.key" :label="item.name"
                      :value="item.key" />
                  </el-select>
                </el-form-item>
              </el-col>
                <el-col :span="6"  >
                  <el-form-item v-if="!isEdit" label-width="80px" label="发布用户:" class="postInfo-container-item">
                    <el-select v-model="postForm.userId" :remote-method="getRemoteUserList" placeholder="请输入用户名/id" filterable   remote >
                      <el-option v-for="(item,index) in userListOptions" :key="item.id" :label="item.nick_name" :value="item.id" />
                    </el-select>
                  </el-form-item>
                  <el-form-item v-if="isEdit"  label-width="80px" label="发布用户:" class="postInfo-container-item">
                    <span> {{ postForm.author }}</span>
                  
                  </el-form-item>
                </el-col>
                <el-col :span="10"  v-if="false">
                  <el-form-item label-width="120px" label="开始时间:" class="postInfo-container-item">
                    <el-date-picker v-model="startTime" type="datetime" format="yyyy-MM-dd HH:mm:ss" placeholder="选择开始时间" />
                  </el-form-item>
                </el-col>
                <el-col :span="10"  v-if="false">
                  <el-form-item label-width="120px" label="结束时间:" class="postInfo-container-item">
                    <el-date-picker v-model="endTime" type="datetime" format="yyyy-MM-dd HH:mm:ss" placeholder="选择结束时间" />
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </el-col>
        </el-row>


        <el-form-item v-if="false" prop="content" style="margin-bottom: 30px;">
          <Tinymce ref="editor" v-model="postForm.content" :height="400" />
        </el-form-item>

        <el-form-item prop="images" style="margin-bottom: 30px;">
          <Upload v-model="postForm.images" />
        </el-form-item>
      </div>
    </el-form>
  </div>
</template>

<script>
import Tinymce from '@/components/Tinymce'
import Upload from '@/components/Upload/SingleImage3'
import MDinput from '@/components/MDinput'
import Sticky from '@/components/Sticky' // 粘性header组件
import { validURL } from '@/utils/validate'
import { fetchArticle,createArticle,updateArticle } from '@/api/article'
import { mockUsers } from '@/api/user'
import Warning from './Warning'
import { CommentDropdown, StatusDropdown,TypeDropdown,PlatformDropdown, SourceUrlDropdown } from './Dropdown'

const defaultForm = {
  status: 'show',
  userId:0,
  type:1,
  title: '', // 文章题目
  content: '', // 文章内容
  images: '', // 文章图片
  id: 0,
  comment_disabled: false,
}

export default {
  name: 'ArticleDetail',
  components: { Tinymce, MDinput, Upload, Sticky, Warning, CommentDropdown,StatusDropdown, TypeDropdown, PlatformDropdown, SourceUrlDropdown },
  props: {
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {
    const validateRequire = (rule, value, callback) => {
      if (value === '') {
        this.$message({
          message: rule.field + '为必传项',
          type: 'error'
        })
        callback(new Error(rule.field + '为必传项'))
      } else {
        callback()
      }
    }
    const validateSourceUri = (rule, value, callback) => {
      if (value) {
        if (validURL(value)) {
          callback()
        } else {
          this.$message({
            message: '外链url填写不正确',
            type: 'error'
          })
          callback(new Error('外链url填写不正确'))
        }
      } else {
        callback()
      }
    }
    return {
      typeOptions : [
        { key: 0, name: '全部' },
        { key: 1, name: '笔记' },
        { key: 2, name: '问答' },
        { key: 3, name: '找搭子' },
        { key: 4, name: '闲置' },
        { key: 5, name: '二手' },

      ],
      postForm: Object.assign({}, defaultForm),
      loading: false,
      userListOptions: [],
      rules: {
        image_uri: [{ validator: validateRequire }],
        title: [{ validator: validateRequire }],
        content: [{ validator: validateRequire }],
        source_uri: [{ validator: validateSourceUri, trigger: 'blur' }]
      },
      tempRoute: {}
    }
  },
  computed: {
    contentShortLength() {
      return this.postForm.content_short.length
    },
   
    startTime: {
      // set and get is useful when the data
      // returned by the back end api is different from the front end
      // back end return => "2013-06-25 06:59:25"
      // front end need timestamp => 1372114765000
      get() {
        return (+new Date(this.postForm.startTime))
      },
      set(val) {
        this.postForm.tartTime = new Date(val)
      }
    },
    endTime: {
      // set and get is useful when the data
      // returned by the back end api is different from the front end
      // back end return => "2013-06-25 06:59:25"
      // front end need timestamp => 1372114765000
      get() {
        return (+new Date(this.postForm.endTime))
      },
      set(val) {
        this.postForm.endTime = new Date(val)
      }
    }
  },
  created() {
    if (this.isEdit) {
      const id = this.$route.params && this.$route.params.id
      this.fetchData(id)
    }
    else{
      this.getRemoteUserList({})
    }

    // Why need to make a copy of this.$route here?
    // Because if you enter this page and quickly switch tag, may be in the execution of the setTagsViewTitle function, this.$route is no longer pointing to the current page
    // https://github.com/PanJiaChen/vue-element-admin/issues/1221
    this.tempRoute = Object.assign({}, this.$route)
  },
  methods: {
    fetchData(id) {
      fetchArticle(id).then(response => {
        this.postForm = response.data

        // set tagsview title
        this.setTagsViewTitle()

        // set page title
        this.setPageTitle()
      }).catch(err => {
        console.log(err)
      })
    },
    setTagsViewTitle() {
      const title = '编辑内容'
      const route = Object.assign({}, this.tempRoute, { title: `${title}-${this.postForm.id}` })
      this.$store.dispatch('tagsView/updateVisitedView', route)
    },
    setPageTitle() {
      const title = '编辑内容'
      document.title = `${title} - ${this.postForm.id}`
    },
    submitForm() {
      console.log(this.postForm)
      this.$refs.postForm.validate(valid => {
        if (valid) {
          this.loading = true
          if (this.isEdit) {
            updateArticle(this.postForm).then(response => {
              this.$notify({
                title: '成功',
                message: '更新成功',
                type: 'success',
                duration: 2000
              })
              this.loading = false
            }).catch(err => {
              this.loading = false
              console.log(err)
            })
          }
          else {
            createArticle(this.postForm).then(response => {
              this.$notify({
                title: '成功',
                message: '发布成功',
                type: 'success',
                duration: 2000
              })
              this.loading = false
            }).catch(err => {
              console.log(err)
              this.loading = false
            })
          }
        } else {
          console.log('error submit!!')
          return false
        }
      })
    },
   
    getRemoteUserList(query) {
      mockUsers(query).then(response => {
        if (!response.data.items) return
        this.userListOptions = response.data.items
      })
    }
  }
}
</script>

<style lang="scss" scoped>
@import "~@/styles/mixin.scss";

.createPost-container {
  position: relative;

  .createPost-main-container {
    padding: 40px 45px 20px 50px;

    .postInfo-container {
      position: relative;
      @include clearfix;
      margin-bottom: 10px;

      .postInfo-container-item {
        float: left;
      }
    }
  }

  .word-counter {
    width: 40px;
    position: absolute;
    right: 10px;
    top: 0px;
  }
}

.article-textarea ::v-deep {
  textarea {
    padding-right: 40px;
    resize: none;
    border: none;
    border-radius: 0px;
    border-bottom: 1px solid #bfcbd9;
  }
}
</style>
