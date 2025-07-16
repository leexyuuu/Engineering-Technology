<template>
  <div class="createPost-container">
    <el-form ref="postForm" :model="postForm" :rules="rules" class="form-container">

      <sticky :z-index="10" :class-name="'sub-navbar ' + postForm.status">
        <StatusDropdown v-model="postForm.status" />

        <el-button v-loading="loading" style="margin-left: 10px;" type="success" @click="submitForm">
          提交
        </el-button>

      </sticky>

      <div class="createPost-main-container">

        <el-row>

          <el-col :span="24">
          

            <el-form-item style="margin-bottom: 40px;" prop="title">
              <MDinput  v-if="postForm.atUserId > 0" v-model="postForm.content" name="回复" required>
                回复用户：{{ atuser }} (“{{ comment }}”): 
              </MDinput>
              <MDinput  v-if="postForm.atUserId <= 0" v-model="postForm.content" name="回复" required>
                回复评论：{{ comment }}
              </MDinput>
            </el-form-item>


            <div class="postInfo-container">
              <el-row>
                <el-col :span="8">
                  <el-form-item v-if="!isEdit" label-width="80px" label="发布用户:" class="postInfo-container-item">
                    <el-select v-model="postForm.userId" :remote-method="getRemoteUserList" remote>
                      <el-option v-for="(item, index) in userListOptions" :key="item.id" :label="item.nick_name"
                        :value="item.id" />
                    </el-select>
                  </el-form-item>

                </el-col>

              </el-row>
            </div>
          </el-col>
        </el-row>


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
import { mockUsers } from '@/api/user'
import Warning from './Warning'
import { StatusDropdown } from './Dropdown'
import { fetchReply, createReply, updateReply } from '@/api/reply'
import { fetchComment } from '@/api/comment'
import { comment } from 'jszip/lib/defaults'
const defaultForm = {
  status: 'show',
  content: '',
  atUserId: 0,
  contentId: 0,
  commentId: 0,
  images: '',
  userId: 0,
  id: undefined
}

export default {
  name: 'RpelyDetail',
  components: { Tinymce, MDinput, Upload, Sticky, Warning, StatusDropdown },
  props: {
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {

    return {
      userListOptions: [],
      comment: '',
      atuser: '',
      postForm: Object.assign({}, defaultForm),
      loading: false,
      tempRoute: {}
    }
  },
  computed: {


  },
  created() {
    if (this.isEdit) {
      const id = this.$route.params && this.$route.params.id
      this.fetchData(id)
    }
    else {

      if (this.$route.query.replyuid) {
        this.postForm.atUserId = parseInt(this.$route.query.replyuid)
        this.atuser = decodeURIComponent(this.$route.query.replyuser)
      }
      this.postForm.commentId = parseInt(this.$route.query.commentid)
      fetchComment(this.postForm.commentId).then(response => {
        this.postForm.contentId = response.data.contentId
        this.comment = response.data.content

      }).catch(err => {
        console.log(err)
      })

      this.getRemoteUserList({})

    }

    // Why need to make a copy of this.$route here?
    // Because if you enter this page and quickly switch tag, may be in the execution of the setTagsViewTitle function, this.$route is no longer pointing to the current page
    // https://github.com/PanJiaChen/vue-element-admin/issues/1221

  },
  methods: {
    fetchData(id) {
      fetchReply(id).then(response => {
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
      const title = '编辑评论'
      const route = Object.assign({}, this.tempRoute, { title: `${title}-${this.postForm.id}` })
      this.$store.dispatch('tagsView/updateVisitedView', route)
    },
    setPageTitle() {
      const title = '编辑评论'
      document.title = `${title} - ${this.postForm.id}`
    },
    submitForm() {
      console.log(this.postForm)
      this.$refs.postForm.validate(valid => {
        if (valid) {
          this.loading = true
          if (this.isEdit) {
            updateReply(this.postForm).then(response => {
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
            createReply(this.postForm).then(response => {
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
