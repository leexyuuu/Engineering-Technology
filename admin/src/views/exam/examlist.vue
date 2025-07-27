<template>
  <div class="app-container">
    <el-button type="primary" @click="handleAdd">添加考试</el-button>
    <el-table :data="examList" style="width: 100%" v-loading="loading">
      <el-table-column prop="id" label="ID" width="120" />
      <el-table-column prop="name" label="考试名称" />
      <el-table-column prop="start_time" label="考试开始时间" />
      <el-table-column prop="end_time" label="考试截止时间" />
      <el-table-column prop="duration_minutes" label="考试时长" />
      <el-table-column label="学生管理">
        <template slot-scope="scope">
          <router-link :to="'/exam/studentlist/'+scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              学生管理
            </el-button>
          </router-link>
        </template>
      </el-table-column>
       <el-table-column align="center" label="题目" width="120">
        <template slot-scope="scope">
          <router-link :to="'/exam/questionlist/'+scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              题目管理
            </el-button>
          </router-link>
        </template>
      </el-table-column>
       <el-table-column align="center" label="管理" width="120">
        <template slot-scope="scope">
          <router-link :to="'/exam/editexam/'+scope.row.id">
            <el-button type="primary" size="small" icon="el-icon-edit">
              编辑
            </el-button>
          </router-link>
        </template>
    
      </el-table-column>
    </el-table>
    <el-pagination
      background
      layout="prev, pager, next"
      :total="total"
      :page-size="pageSize"
      :current-page.sync="page"
      @current-change="fetchList"
    />
  </div>
</template>

<script>
import { fetchExamList, deleteExam } from "@/api/exam";
export default {
  data() {
    return {
      examList: [],
      loading: false,
      total: 0,
      page: 1,
      pageSize: 50,
    };
  },
  created() {
    this.fetchList();
  },
  methods: {
    fetchList() {
      this.loading = true;
      fetchExamList({ page: this.page, page_size: this.pageSize })
        .then((res) => {
          this.examList = res.data.items || [];
          this.total = res.data.total || 0;
          this.loading = false;
        })
        .catch(() => {
          this.loading = false;
        });
    },
    handleAdd() {
      this.$router.push({ path: "/exam/editexam" });
    },
    handleEdit(row) {
      this.$router.push({ path: `/exam/editexam/${row.id}` });
    },
    handleDelete(row) {
      this.$confirm("确定删除该考试吗？", "提示", { type: "warning" }).then(
        () => {
          deleteExam(row.id).then(() => {
            this.$message.success("删除成功");
            this.fetchList();
          });
        }
      );
    },
    goQuestionList(row) {
      this.$router.push({ path: `/exam/questionlist/
      ${row.id}` });
    },
    goStudentList(row) {
      this.$router.push({ path: `/exam/studentlist/${row.id}` });
    },
  },
};
</script> 