<template>
  <div class="app-container">
    <div class="createPost-container">
      <el-form class="form-container">
        <div class="createPost-main-container">
          <div class="postInfo-container">
            <el-row>
              <el-col :span="3">
                <el-form-item label-width="60px" label="类型" class="postInfo-container-item">
                  <el-select v-model="listQuery.type" filterable default-first-option>
                    <el-option v-for="(item, index) in typeOptions" :key="item.key" :label="item.name"
                      :value="item.key" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="3">
                <el-form-item label-width="60px" label="用户:" class="postInfo-container-item">
                  <el-select v-model="listQuery.userId" :remote-method="getUserList" filterable remote
                    placeholder="请输入用户名/id">
                    <el-option v-for="(item, index) in userListOptions" :key="item.id" :label="item.nick_name"
                      :value="item.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="3">
                <el-form-item label-width="60px" label="社区:" class="postInfo-container-item">
                  <el-select v-model="listQuery.areaId" @change="handleAreaChange" :remote-method="getAreaList"
                    filterable remote placeholder="请输入名称">
                    <el-option v-for="(item, index) in areaListOptions" :key="item.id" :label="item.name"
                      :value="item.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="3">
                <el-form-item label-width="60px" label="单元:" class="postInfo-container-item">
                  <el-select v-model="listQuery.cellId" filterable placeholder="请输入名称">
                    <el-option v-for="(item, index) in areaListOptions" :key="item.id" :label="item.name"
                      :value="item.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="7">
                <el-form-item label-width="60px" label="内容:" class="postInfo-container-item">
                  <el-input placeholder="请输入文字" style="" v-model="listQuery.txt" />
                </el-form-item>
              </el-col>

              <el-col :span="5">

                <el-button type="success" @click="search" style="margin-left: 20px;" size="small" icon="el-icon-search">
                  开始搜索
                </el-button>

                <router-link :to="'/example/create'" style="margin-left: 20px;">
                  <el-button type="primary" size="small" icon="el-icon-edit">
                    新增内容
                  </el-button>
                </router-link>
              </el-col>

            </el-row>
          </div>
        </div>
      </el-form>

    </div>


    <el-table v-loading="listLoading" :data="list" border fit highlight-current-row style="width: 100%">
      <el-table-column align="center" label="ID" width="80">
        <template slot-scope="scope">
          <span>{{ scope.row.id }}</span>
        </template>
      </el-table-column>


      <el-table-column width="120px" align="center" label="用户">
        <template slot-scope="scope">
          <span>{{ scope.row.author }}</span>
        </template>
      </el-table-column>
      <el-table-column width="120px" align="center" label="社区">
        <template slot-scope="scope">
          <span>{{ scope.row.area }}</span>
        </template>
      </el-table-column>
      <el-table-column width="120px" align="center" label="类型">
        <template slot-scope="scope">
          <span> {{ scope.row.typeDes }}</span>
        </template>
      </el-table-column>
      <el-table-column width="350px" label="内容">
        <template slot-scope="{row}">
          <router-link :to="'/example/edit/' + row.id" class="link-type">
            <span>{{ row.title }}</span>
          </router-link>
        </template>
      </el-table-column>

      <el-table-column width="120px" align="center" label="时间">
        <template slot-scope="scope">
          <span>{{ scope.row.timestamp }}</span>
        </template>
      </el-table-column>


      <el-table-column class-name="status-col" label="状态" width="80">
        <template slot-scope="{row}">
          <el-tag :type="row.status | statusFilter">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column align="center" label="操作" width="360">
        <template slot-scope="scope">
          <router-link :to="'/example/edit/' + scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              编辑
            </el-button>
          </router-link>
          <router-link style="margin-left: 20px;"
            :to="'/example/commentlist?cid=' + scope.row.id + '&title=' + encodeURIComponent(scope.row.title)">
            <el-button type="primary" size="small" icon="el-icon-edit">
              评论
            </el-button>
          </router-link>
          <router-link
          style="margin-left: 20px;"
            :to="'/example/createcomment?cid=' + scope.row.id + '&title=' + encodeURIComponent(scope.row.title)">
            <el-button type="primary" size="small" icon="el-icon-edit">
              添加评论
            </el-button>
          </router-link>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total > 20" :total="total" :page.sync="listQuery.page" :limit.sync="listQuery.limit"
      @pagination="getList" />
  </div>
</template>

<script>
import { searchArticle } from '@/api/article'
import { searchArea } from '@/api/area'
import { searchCell } from '@/api/cell'
import { searchUser } from '@/api/user'
import Pagination from '@/components/Pagination' // Secondary package based on el-pagination

export default {
  name: 'ArticleList',
  components: { Pagination },
  filters: {
    statusFilter(status) {
      const statusMap = {
        published: 'success',
        draft: 'info',
        deleted: 'danger'
      }
      return statusMap[status]
    },

  },
  data() {
    return {
      list: null,
      total: 0,
      userListOptions: [],
      areaListOptions: [],
      cellListOptions: [],
      typeOptions: [
        { key: 0, name: '全部' },
        { key: 1, name: '笔记' },
        { key: 2, name: '问答' },
        { key: 3, name: '找搭子' },
        { key: 4, name: '闲置' },
        { key: 5, name: '二手' },

      ],
      listLoading: true,
      listQuery: {
        txt: '',
        userId: 0,
        areaId: 0,
        type: 0,
        cellId: 0,
        page: 1,
        limit: 20
      }
    }
  },
  created() {
    this.getList()
    this.getAreaList()
  },
  mounted: {


  },
  computed: {

  },
  methods: {

    search() {
      this.listQuery.page = 1
      this.getList()
    },
    typeFilter(type) {
      this.typeOptions.forEach(function (item, index) {
        if (item.key == type) {
          return item.name
        }
        return "未知"
      });
    },
    getList() {
      this.listLoading = true
      const typeOptions = this.typeOptions
      searchArticle(this.listQuery).then(response => {
        const items = response.data.items
        items.forEach(function (item, index) {
          typeOptions.forEach(function (type, index) {
            if (type.key == item.type) {
              item.typeDes = type.name
            }

          });
        });
        this.list = items
        this.total = response.data.total
        this.listLoading = false
      })
    },
    getUserList(query) {
      searchUser(query).then(response => {
        if (!response.data.items) return
        this.userListOptions = response.data.items
      })
    },
    handleAreaChange(id) {
      const value = this.areaListOptions.find(item => item.id == id)
      this.listQuery.cityId = value.cityId
      this.listQuery.areaId = value.id
      this.listQuery.cellId = 0
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
  }
}
</script>

<style scoped>
.edit-input {
  padding-right: 100px;
}

.cancel-btn {
  position: absolute;
  right: 15px;
  top: 10px;
}
</style>
