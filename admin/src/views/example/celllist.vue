<template>
  <div class="app-container">
    <div class="postInfo-container" style="margin-bottom: 20px;">
      <el-row>

        <el-col :span="7">
          <el-input placeholder="搜索名字" style="" v-model="searchQuery"
            @input="handleInput" />
        </el-col>
        <el-col :span="1">
          <router-link :to="'/example/createcell'" style="margin-left: 20px;">
            <el-button type="primary" size="small" icon="el-icon-edit">
              新增
            </el-button>
          </router-link>
        </el-col>
      </el-row>
    </div>


    <el-table v-loading="listLoading" :data="list" border fit highlight-current-row style="width: 100%">
      <el-table-column align="center" label="ID" width="80">
        <template slot-scope="scope">
          <span>{{ scope.row.id }}</span>
        </template>
      </el-table-column>



      <el-table-column width="100px" label="Name">
        <template slot-scope="{row}">
          <router-link :to="'/example/editcell/' + row.id" class="link-type">
            <span>{{ row.name }}</span>
          </router-link>
        </template>
      </el-table-column>
      <el-table-column width="100px" label="Area">
        <template slot-scope="{row}">
            <span>{{ row.area }}</span>
      
        </template>
      </el-table-column>

      <el-table-column class-name="status-col" label="Status" width="110">
        <template slot-scope="{row}">
          <el-tag :type="row.status | statusFilter">
            {{ row.status }}
          </el-tag>
        </template>
        
      </el-table-column>


      <el-table-column align="center" label="Actions" width="120">
        <template slot-scope="scope">
          <router-link :to="'/example/editcell/' + scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              Edit
            </el-button>
          </router-link>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total > 20&&this.searchQuery.length == 0" :total="total" :page.sync="listQuery.page" :limit.sync="listQuery.limit"
      @pagination="getList" />
  </div>
</template>

<script>
import { fetchCellList, searchCell } from '@/api/cell'
import Pagination from '@/components/Pagination' // Secondary package based on el-pagination
import Search from '@/components/HeaderSearch'

export default {
  name: 'CellList',
  components: { Pagination, Search },
  filters: {
    statusFilter(status) {
      const statusMap = {
        show: 'success',
        hide: 'danger'
      }
      return statusMap[status]
    }
  },
  data() {
    return {
      list: null,
      total: 0,
      listLoading: true,
      searchQuery: '',
      listQuery: {
        page: 1,
        limit: 20
      }
    }
  },
  created() {
    this.getList()
  },
  methods: {
    handleInput() {
      this.getList()
    },
    getList() {
      this.listLoading = true
      if (this.searchQuery.length > 0) {
        searchCell(this.searchQuery).then(response => {
          this.list = response.data.items
          this.total = response.data.total
          this.listLoading = false
        })
      }
      else {
        fetchCellList(this.listQuery).then(response => {
          this.list = response.data.items
          this.total = response.data.total
          this.listLoading = false
        })
      }
    }
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
