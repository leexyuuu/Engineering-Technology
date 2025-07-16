<template>
  <div class="createPost-container">
    <el-form ref="postForm" :model="postForm" :rules="rules" class="form-container">

      <sticky :z-index="10" :class-name="'sub-navbar ' + postForm.status">
        <StatusDropdown v-model="postForm.status" />
        <el-button v-loading="loading" style="margin-left: 10px;" type="success" @click="submitForm">
          发布
        </el-button>

      </sticky>

      <div class="createPost-main-container">
        <el-row v-if="!isEdit">
    
          <el-col :span="24">
            <div class="postInfo-container">
              <el-row>
                <el-col :span="8">
                  <el-form-item label-width="60px" label="社区:" class="postInfo-container-item">
                    <el-select @change="changeArea" v-model="postForm.areaItem" :remote-method="getAreaList" filterable default-first-option remote placeholder="搜索社区">
                      <el-option v-for="(item,index) in areaListOptions" :key="item.id" :label="item.name" :value="item" />
                    </el-select>
                  </el-form-item>
                </el-col>
              </el-row>
            </div>
          </el-col>
        </el-row>

      
        <el-form-item style="margin-bottom: 40px;" label-width="70px" label="名称:">
          <el-input v-model="postForm.name" :rows="1" type="textarea" class="article-textarea" autosize
            placeholder="请输入单元名称" />
        </el-form-item>
        <el-form-item style="margin-bottom: 40px;" label-width="70px" label="简介:">
          <el-input v-model="postForm.summary" :rows="1" type="textarea" class="article-textarea" autosize
            placeholder="请输入单元简介" />
        </el-form-item>

        <el-form-item prop="icon" style="margin-bottom: 30px;" label-width="70px" label="图标:">
          <Upload v-model="postForm.icon" />
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
import { fetchCell, createCell, updateCell } from '@/api/cell'
import { searchArea } from '@/api/area'
import Warning from './Warning'
import { StatusDropdown } from './Dropdown'

const defaultForm = {
  status: 'show',
  cityId:0,
  areaId:0,
  area:"",
  name: '', 
  summary: '', 
  index: 0, 
  icon: '',
  id: 0,
  areaItem:{}
}

export default {
  name: 'CellDetail',
  components: { Tinymce, MDinput, Upload, Sticky, Warning, StatusDropdown },
  props: {
    isEdit: {
      type: Boolean,
      default: false
    }
  },
  data() {
    const validateRequire = (rule, value, callback) => {
      if (value === ''||value.length<2) {
        this.$message({
          message: rule.field + '为必传项',
          type: 'error'
        })
        callback(new Error(rule.field + '为必传项'))
      } else {
        callback()
      }
    }

    return {
      postForm: Object.assign({}, defaultForm),
      loading: false,
      areaListOptions: [],
      rules: {
        name: [{ validator: validateRequire }]
      },
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
    else{
      this.getAreaList("")
    }

    // Why need to make a copy of this.$route here?
    // Because if you enter this page and quickly switch tag, may be in the execution of the setTagsViewTitle function, this.$route is no longer pointing to the current page
    // https://github.com/PanJiaChen/vue-element-admin/issues/1221
    this.tempRoute = Object.assign({}, this.$route)
  },
  methods: {
    fetchData(id) {
      fetchCell(id).then(response => {
        this.postForm = response.data

        // just for test
        this.postForm.title += `   Cell Id:${this.postForm.id}`
        this.postForm.content_short += `   Cell Id:${this.postForm.id}`

        // set tagsview title
        this.setTagsViewTitle()

        // set page title
        this.setPageTitle()
      }).catch(err => {
        console.log(err)
      })
    },
    changeArea(item){
      this.postForm.areaId=item.areaId
      this.postForm.cityId=item.cityId
    },
    setTagsViewTitle() {
      const title = '编辑单元'
      const route = Object.assign({}, this.tempRoute, { title: `${title}-${this.postForm.id}` })
      this.$store.dispatch('tagsView/updateVisitedView', route)
    },
    setPageTitle() {
      const title = '编辑单元'
      document.title = `${title} - ${this.postForm.id}`
    },
    submitForm() {
      console.log(this.postForm)
      this.$refs.postForm.validate(valid => {
        if (valid) {
          this.loading = true
          if (this.isEdit) {
            updateCell(this.postForm).then(response => {
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
            createCell(this.postForm).then(response => {
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
          this.loading = false
          return false
        }
      })
    },
    getAreaList(query) {
      searchArea(query).then(response => {
        if (!response.data.items) return
        this.areaListOptions = response.data.items
        if(this.postForm.areaId==0)
        {
          this.postForm.areaItem=this.areaListOptions[0]
          this.postForm.areaId= this.areaListOptions[0].id
          this.postForm.cityId=this.areaListOptions[0].cityId
        }
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
