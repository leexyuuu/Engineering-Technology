<template>
  <div class="createPost-container">
    <el-form ref="postForm" :model="postForm" :rules="rules" class="form-container">

      <sticky :z-index="10" :class-name="'sub-navbar '">

        <el-button v-loading="loading" style="margin-left: 10px;" type="success" @click="submitForm">
          提交
        </el-button>

      </sticky>

      <div class="createPost-main-container">
        <div class="postInfo-container">
          <el-row>
            <el-col :span="3">
              <el-form-item label-width="60px" label="状态" class="postInfo-container-item">
                <el-select v-model="postForm.status" filterable default-first-option>
                  <el-option v-for="(item, index) in statusOptions" :key="item.key" :label="item.name"
                    :value="item.key" />
                </el-select>
              </el-form-item>
            </el-col>

            <el-col :span="3">
              <el-form-item label-width="60px" label="性别" class="postInfo-container-item">
                <el-select v-model="postForm.gender" filterable default-first-option>
                  <el-option v-for="(item, index) in genderOptions" :key="item.key" :label="item.name"
                    :value="item.key" />
                </el-select>
              </el-form-item>
            </el-col>

            <el-col :span="3">
              <el-form-item label-width="60px" label="社区:" class="postInfo-container-item">
                <el-select @change="handleAreaChange" v-model="postForm.areaId" :remote-method="getAreaList" filterable
                  remote placeholder="请输入名称">
                  <el-option v-for="(item, index) in areaListOptions" :key="item.id" :label="item.name"
                    :value="item.id" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="3">
              <el-form-item label-width="60px" label="单元:" class="postInfo-container-item">
                <el-select v-model="postForm.cellId" filterable placeholder="请选择名称">
                  <el-option v-for="(item, index) in cellListOptions" :key="item.id" :label="item.name"
                    :value="item.id" />
                </el-select>
              </el-form-item>
            </el-col>

          </el-row>
        </div>

        <el-form-item style="margin-bottom: 40px;" label-width="70px" label="昵称:">
          <el-input v-model="postForm.nick_name" :rows="1" type="textarea" class="article-textarea" autosize
            placeholder="请输入昵称" />
        </el-form-item>
        <el-form-item style="margin-bottom: 40px;" label-width="70px" label="简介:">
          <el-input v-model="postForm.summary" :rows="1" type="textarea" class="article-textarea" autosize
            placeholder="请输入简介" />
        </el-form-item>

        <el-form-item prop="avatar_url" style="margin-bottom: 30px;">
          <Upload v-model="postForm.avatar_url" />
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
import { addMockuser, updateUser, fetchUser } from '@/api/user'
import { searchArea } from '@/api/area'
import { searchCell } from '@/api/cell'
import Warning from './Warning'
import { StatusDropdown } from './Dropdown'

const defaultForm = {
  status: 0,
  avatar_url: '',
  areaId: 0,
  cellId: 0,
  cityId: 0,
  gender: 0,
  nick_name: "",
  birth:"",
  address:"",
  summary: "",
  id: undefined
}

export default {
  name: 'UserDetail',
  components: { Tinymce, MDinput, Upload, Sticky, Warning, StatusDropdown },
  props: {
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {

    return {
      typeListOptions: [],
      genderListOptions: [],
      areaListOptions: [],
      cellListOptions: [],
      statusOptions: [
        { key: 0, name: '正常' },
        { key: 1, name: '禁言' },
      ],
      genderOptions: [
        { key: 0, name: '未知' },
        { key: 1, name: '男' },
        { key: 2, name: '女' }
      ],
      postForm: Object.assign({}, defaultForm),
      loading: false,
      tempRoute: {}
    }
  },
  computed: {


  },
  created() {
    this.getAreaList()
    if (this.isEdit) {
      const id = this.$route.params && this.$route.params.id
      this.fetchData(id)
    }
    else {
      this.postForm.commentId = this.$route.params.cid
      this.postForm.comment = decodeURIComponent(this.$route.params.comment)
    }

    // Why need to make a copy of this.$route here?
    // Because if you enter this page and quickly switch tag, may be in the execution of the setTagsViewTitle function, this.$route is no longer pointing to the current page
    // https://github.com/PanJiaChen/vue-element-admin/issues/1221
    this.tempRoute = Object.assign({}, this.$route)
  },
  methods: {
    fetchData(id) {
      fetchUser(id).then(response => {
        this.postForm = response.data
        if (this.postForm.areaId > 0) {
          this.getCellList(this.postForm.areaId)
        }

        // set tagsview title
        this.setTagsViewTitle()

        // set page title
        this.setPageTitle()
      }).catch(err => {
        console.log(err)
      })
    },
    setTagsViewTitle() {
      const title = '编辑用户'
      const route = Object.assign({}, this.tempRoute, { title: `${title}-${this.postForm.id}` })
      this.$store.dispatch('tagsView/updateVisitedView', route)
    },
    setPageTitle() {
      const title = '编辑用户'
      document.title = `${title} - ${this.postForm.id}`
    },
    submitForm() {
      console.log(this.postForm)
      this.$refs.postForm.validate(valid => {
        if (valid) {
          this.loading = true
          if (this.isEdit) {
            updateUser(this.postForm).then(response => {
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
            addMockuser(this.postForm).then(response => {
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
    handleAreaChange(id) {
      const value = this.areaListOptions.find(item => item.id == id)
      this.postForm.cityId = value.cityId
      this.postForm.areaId = value.id
      this.postForm.cellId = 0
      this.cellListOptions = []
      this.getCellList(value.id)
    },
    getAreaList(query) {
      searchArea(query).then(response => {
        if (!response.data.items) return
        this.areaListOptions = response.data.items
      })
    },
    getCellList(areaId) {
      const params = {}
      params.areaId = areaId
      searchCell(params).then(response => {
        if (!response.data.items) return
        this.cellListOptions = response.data.items
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
