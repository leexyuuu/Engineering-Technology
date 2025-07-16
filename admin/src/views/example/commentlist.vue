<template>
  <div class="app-container">
    <div class="createPost-container">
      <el-form class="form-container">
        <div class="createPost-main-container">
          <div class="postInfo-container">
            <el-row>
              <el-col :span="3">
                <el-form-item label-width="60px" label="用户:" class="postInfo-container-item">
                  <el-select v-model="listQuery.userId" :remote-method="getUserList" filterable default-first-option
                    remote placeholder="请输入用户名/id">
                    <el-option v-for="(item, index) in userListOptions" :key="item.id"
                      :label="item.nick_name + '(' + item.id + ')'" :value="item.id" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="3">
                <el-form-item label-width="60px" label="帖子:" class="postInfo-container-item">
                  <el-select v-if="title == ''" v-model="listQuery.contentId" :remote-method="getContentList" filterable
                    default-first-option remote placeholder="请输入文字">
                    <el-option v-for="(item, index) in contentListOptions" :key="item.id" :label="item.title"
                      :value="item.id" />
                  </el-select>
                  <label>{{ title }}</label>
                </el-form-item>
              </el-col>
              <el-col :span="7">
                <el-form-item label-width="60px" label="评论:" class="postInfo-container-item">
                  <el-input placeholder="请输入文字" style="" v-model="listQuery.txt" />
                </el-form-item>
              </el-col>

              <el-col :span="5">
                <el-button type="success" @click="search" style="margin-left: 20px;" size="small" icon="el-icon-search">
                  开始搜索
                </el-button>

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

      <el-table-column width="160px" align="center" label="时间">
        <template slot-scope="scope">
          <span>{{ scope.row.timestamp  }}</span>
        </template>
      </el-table-column>

      <el-table-column width="120px" align="center" label="用户">
        <template slot-scope="scope">
          <router-link :to="'/example/commentlist?uid=' + scope.row.userId">
            <span>{{ scope.row.nick_name }}</span>
          </router-link>
        </template>
      </el-table-column>
      <el-table-column width="120px" align="center" label="评论">
        <template slot-scope="scope">
          <span>{{ scope.row.content }}</span>
        </template>
      </el-table-column>
      <el-table-column width="120px" align="center" label="帖子">
        <template slot-scope="scope">
          <router-link :to="'/example/commentlist?cid=' + scope.row.contentId">
            <span>{{ scope.row.title }}</span>
          </router-link>
        </template>
      </el-table-column>
      <el-table-column align="center" label="是否置顶" width="120px">
        <template slot-scope="scope">
          <span>{{ scope.row.top }}</span>
        </template>
      </el-table-column>
      <el-table-column class-name="status-col" label="状态" width="110">
        <template slot-scope="scope">
          <el-tag :type="scope.row.status | statusFilter">
            {{ scope.row.status }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column align="center" label="操作" width="200">
        <template slot-scope="scope">
          <router-link :to="'/example/editcomment/' + scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              编辑
            </el-button>
          </router-link>
          <router-link style="margin-left: 20px;" :to="'/example/replylist?cid=' + scope.row.id + '&comment=' + encodeURIComponent(scope.row.content)">
            <el-button type="primary" size="small" icon="el-icon-edit">
              回复
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
import { fetchList } from '@/api/comment'
import { searchArticle } from '@/api/article'
import { searchUser } from '@/api/user'
import Pagination from '@/components/Pagination' // Secondary package based on el-pagination


export default {
  name: 'CommentList',
  components: { Pagination },
  filters: {
    statusFilter(status) {
      const statusMap = {
        show: 'success',
        hide: 'danger'
      }
      return statusMap[status]
    },
    timeFilter(timestamp) {

      return new Date(timestamp).toDateString()
    }
  },
  data() {
    return {
      list: [],
      total: 0,
      userListOptions: [],
      contentListOptions: [],
      listLoading: true,
      title: '',
      listQuery: {
        txt: '',
        userId: 0,
        contentId: 0,
        page: 1,
        limit: 20
      }
    }
  },
  created() {
    if (this.$route.query && this.$route.query.uid) {
      this.listQuery.userId= this.$route.query.uid
    }
    if (this.$route.query && this.$route.query.cid) {
      this.listQuery.contentId = this.$route.query.cid

      if (this.listQuery.contentId > 0) {
        this.title = decodeURIComponent(this.$route.query.title)
      }
    }

    this.getList()
  },
  methods: {
    search() {
      this.listQuery.page = 1
      this.getList()

    },
    getList() {
      this.listLoading = true
      fetchList(this.listQuery).then(response => {
        this.list = response.data.items
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
    getContentList(query) {
      searchArticle(query).then(response => {
        if (!response.data.items) return
        this.contentListOptions = response.data.items
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
